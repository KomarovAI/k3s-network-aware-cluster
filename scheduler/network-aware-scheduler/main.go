package main

import (
	"context"
	"flag"
	"fmt"
	"os"
	"strconv"
	"strings"
	"time"

	v1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/client-go/informers"
	"k8s.io/client-go/kubernetes"
	"k8s.io/client-go/rest"
	"k8s.io/client-go/tools/clientcmd"
	"k8s.io/klog/v2"
	"k8s.io/kubernetes/pkg/scheduler"
	"k8s.io/kubernetes/pkg/scheduler/framework"
	"k8s.io/kubernetes/pkg/scheduler/framework/plugins/defaultbinder"
	"k8s.io/kubernetes/pkg/scheduler/framework/plugins/queuesort"
	frameworkruntime "k8s.io/kubernetes/pkg/scheduler/framework/runtime"
	"k8s.io/kubernetes/pkg/scheduler/profile"

	networktopologyv1 "github.com/KomarovAI/k3s-network-aware-cluster/pkg/apis/networktopology/v1"
	networktopologyclient "github.com/KomarovAI/k3s-network-aware-cluster/pkg/client/clientset/versioned"
)

const (
	// SchedulerName is the name of the network-aware scheduler
	SchedulerName = "network-aware-scheduler"
	
	// Annotation keys for network requirements
	MinBandwidthAnnotation = "network.komarov.dev/min-bandwidth"
	MaxLatencyAnnotation   = "network.komarov.dev/max-latency"
	DataLocalityAnnotation = "network.komarov.dev/data-locality"
	InternetAccessAnnotation = "network.komarov.dev/internet-access"
	
	// Label keys for node characteristics
	NetworkSpeedLabel = "network-speed"
	NetworkLatencyLabel = "network-latency"
	ZoneLabel = "zone"
	RoleLabel = "role"
	GPULabel = "gpu"
)

// NetworkAwarePlugin implements the network-aware scheduling logic
type NetworkAwarePlugin struct {
	handle            framework.Handle
	topologyClient    networktopologyclient.Interface
	topologyName      string
}

// Name returns the plugin name
func (p *NetworkAwarePlugin) Name() string {
	return "NetworkAware"
}

// Filter filters nodes based on network requirements
func (p *NetworkAwarePlugin) Filter(ctx context.Context, state *framework.CycleState, pod *v1.Pod, nodeInfo *framework.NodeInfo) *framework.Status {
	node := nodeInfo.Node()
	
	klog.V(4).InfoS("Filtering node for pod", "node", node.Name, "pod", klog.KObj(pod))
	
	// Check minimum bandwidth requirement
	if minBw := pod.Annotations[MinBandwidthAnnotation]; minBw != "" {
		required := parseBandwidth(minBw)
		available := p.getNodeBandwidth(node)
		
		if available < required {
			return framework.NewStatus(framework.Unschedulable, 
				fmt.Sprintf("insufficient bandwidth: required %dmbps, available %dmbps", required, available))
		}
		klog.V(4).InfoS("Bandwidth check passed", "node", node.Name, "required", required, "available", available)
	}
	
	// Check maximum latency requirement
	if maxLat := pod.Annotations[MaxLatencyAnnotation]; maxLat != "" {
		required := parseLatency(maxLat)
		nodeLatency := p.getNodeLatency(node, pod)
		
		if nodeLatency > required {
			return framework.NewStatus(framework.Unschedulable,
				fmt.Sprintf("latency too high: required %dms, node %dms", required, nodeLatency))
		}
		klog.V(4).InfoS("Latency check passed", "node", node.Name, "required", required, "actual", nodeLatency)
	}
	
	// Check data locality requirement
	if locality := pod.Annotations[DataLocalityAnnotation]; locality == "high" {
		if node.Labels[ZoneLabel] == "remote" {
			return framework.NewStatus(framework.Unschedulable, "high data locality required, but node is remote")
		}
		klog.V(4).InfoS("Data locality check passed", "node", node.Name, "zone", node.Labels[ZoneLabel])
	}
	
	// Check internet access requirement
	if internetAccess := pod.Annotations[InternetAccessAnnotation]; internetAccess == "required" {
		if node.Labels[RoleLabel] != "public-gateway" && node.Labels[ZoneLabel] != "remote" {
			return framework.NewStatus(framework.Unschedulable, "internet access required, but node has no public access")
		}
		klog.V(4).InfoS("Internet access check passed", "node", node.Name, "role", node.Labels[RoleLabel])
	}
	
	return framework.NewStatus(framework.Success, "")
}

// Score scores nodes based on network characteristics
func (p *NetworkAwarePlugin) Score(ctx context.Context, state *framework.CycleState, pod *v1.Pod, nodeName string) (int64, *framework.Status) {
	nodeInfo, err := p.handle.SnapshotSharedLister().NodeInfos().Get(nodeName)
	if err != nil {
		return 0, framework.AsStatus(err)
	}
	
	node := nodeInfo.Node()
	score := int64(0)
	
	klog.V(4).InfoS("Scoring node for pod", "node", nodeName, "pod", klog.KObj(pod))
	
	// Get network topology data
	topology, err := p.getNetworkTopology(ctx)
	if err != nil {
		klog.V(2).InfoS("Failed to get network topology, using node labels", "error", err)
		return p.scoreFromNodeLabels(node, pod), framework.NewStatus(framework.Success, "")
	}
	
	// Score based on topology data
	score = p.scoreFromTopology(topology, node, pod)
	
	klog.V(4).InfoS("Node scored", "node", nodeName, "score", score)
	return score, framework.NewStatus(framework.Success, "")
}

// getNetworkTopology retrieves the network topology CRD
func (p *NetworkAwarePlugin) getNetworkTopology(ctx context.Context) (*networktopologyv1.NetworkTopology, error) {
	topology, err := p.topologyClient.NetworkV1().NetworkTopologies().Get(ctx, p.topologyName, metav1.GetOptions{})
	if err != nil {
		return nil, fmt.Errorf("failed to get network topology %s: %w", p.topologyName, err)
	}
	return topology, nil
}

// scoreFromTopology calculates score based on topology data
func (p *NetworkAwarePlugin) scoreFromTopology(topology *networktopologyv1.NetworkTopology, node *v1.Node, pod *v1.Pod) int64 {
	score := int64(0)
	nodeName := node.Name
	
	nodeSpec, exists := topology.Spec.Nodes[nodeName]
	if !exists {
		klog.V(3).InfoS("Node not found in topology, using defaults", "node", nodeName)
		return p.scoreFromNodeLabels(node, pod)
	}
	
	// Bonus for high bandwidth
	maxBandwidth := int64(0)
	for _, bwStr := range nodeSpec.Bandwidth {
		if bw := parseBandwidth(bwStr); bw > maxBandwidth {
			maxBandwidth = bw
		}
	}
	score += maxBandwidth / 10 // 10mbps = 1 point, 100mbps = 10 points
	
	// Penalty for high latency
	minLatency := int64(1000) // Start with high value
	for _, latStr := range nodeSpec.Latency {
		if lat := parseLatency(latStr); lat < minLatency {
			minLatency = lat
		}
	}
	if minLatency < 1000 {
		score -= minLatency / 5 // Every 5ms = -1 point
	}
	
	// Penalty for high cost
	minCost := 1.0
	for _, cost := range nodeSpec.Cost {
		if cost < minCost {
			minCost = cost
		}
	}
	score -= int64(minCost * 50) // cost 0.8 = -40 points
	
	return score + p.scoreWorkloadPreference(node, pod)
}

// scoreFromNodeLabels calculates score from node labels when topology is unavailable
func (p *NetworkAwarePlugin) scoreFromNodeLabels(node *v1.Node, pod *v1.Pod) int64 {
	score := int64(0)
	
	// Score based on network speed label
	if speedStr := node.Labels[NetworkSpeedLabel]; speedStr != "" {
		if speed := parseBandwidth(speedStr); speed > 0 {
			score += speed / 10
		}
	}
	
	// Penalty for high latency label
	if latencyLabel := node.Labels[NetworkLatencyLabel]; latencyLabel == "high" {
		score -= 20
	}
	
	return score + p.scoreWorkloadPreference(node, pod)
}

// scoreWorkloadPreference gives preference to specialized nodes
func (p *NetworkAwarePlugin) scoreWorkloadPreference(node *v1.Node, pod *v1.Pod) int64 {
	score := int64(0)
	
	// Strong preference for AI workloads on AI workers
	if workloadType := pod.Labels["workload-type"]; workloadType == "ai" {
		if node.Labels[RoleLabel] == "ai-worker" {
			score += 100
		}
		// Bonus for GPU nodes
		if node.Labels[GPULabel] == "nvidia" {
			score += 50
		}
	}
	
	// Strong preference for web workloads on public gateways
	if workloadType := pod.Labels["workload-type"]; workloadType == "web" {
		if node.Labels[RoleLabel] == "public-gateway" {
			score += 100
		}
		// Bonus for remote nodes with internet access
		if node.Labels[ZoneLabel] == "remote" {
			score += 30
		}
	}
	
	// Preference for local zone for data-intensive workloads
	if locality := pod.Annotations[DataLocalityAnnotation]; locality == "high" {
		if node.Labels[ZoneLabel] == "local" {
			score += 75
		}
	}
	
	return score
}

// getNodeBandwidth extracts bandwidth from node labels
func (p *NetworkAwarePlugin) getNodeBandwidth(node *v1.Node) int64 {
	if speedStr := node.Labels[NetworkSpeedLabel]; speedStr != "" {
		return parseBandwidth(speedStr)
	}
	return 10 // Default 10mbps
}

// getNodeLatency calculates latency for the node
func (p *NetworkAwarePlugin) getNodeLatency(node *v1.Node, pod *v1.Pod) int64 {
	// Check if latency is explicitly labeled
	if latencyLabel := node.Labels[NetworkLatencyLabel]; latencyLabel != "" {
		switch latencyLabel {
		case "low":
			return 5
		case "medium":
			return 25
		case "high":
			return 100
		}
	}
	
	// Estimate based on zone
	if zone := node.Labels[ZoneLabel]; zone == "remote" {
		return 45 // Typical international latency
	}
	
	return 1 // Local latency
}

// parseBandwidth parses bandwidth string to mbps
func parseBandwidth(bandwidth string) int64 {
	bandwidth = strings.ToLower(strings.TrimSpace(bandwidth))
	
	if strings.HasSuffix(bandwidth, "mbps") {
		valStr := strings.TrimSuffix(bandwidth, "mbps")
		if val, err := strconv.ParseInt(valStr, 10, 64); err == nil {
			return val
		}
	}
	
	if strings.HasSuffix(bandwidth, "gbps") {
		valStr := strings.TrimSuffix(bandwidth, "gbps")
		if val, err := strconv.ParseFloat(valStr, 64); err == nil {
			return int64(val * 1000)
		}
	}
	
	if strings.HasSuffix(bandwidth, "kbps") {
		valStr := strings.TrimSuffix(bandwidth, "kbps")
		if val, err := strconv.ParseFloat(valStr, 64); err == nil {
			return int64(val / 1000)
		}
	}
	
	return 0
}

// parseLatency parses latency string to milliseconds
func parseLatency(latency string) int64 {
	latency = strings.ToLower(strings.TrimSpace(latency))
	
	if strings.HasSuffix(latency, "ms") {
		valStr := strings.TrimSuffix(latency, "ms")
		if val, err := strconv.ParseInt(valStr, 10, 64); err == nil {
			return val
		}
	}
	
	return 1000 // Default high latency
}

// New creates a new NetworkAwarePlugin
func New(obj runtime.Object, h framework.Handle) (framework.Plugin, error) {
	// Build Kubernetes client
	config, err := rest.InClusterConfig()
	if err != nil {
		// Fallback to kubeconfig
		kubeconfig := os.Getenv("KUBECONFIG")
		if kubeconfig == "" {
			kubeconfig = os.Getenv("HOME") + "/.kube/config"
		}
		config, err = clientcmd.BuildConfigFromFlags("", kubeconfig)
		if err != nil {
			return nil, fmt.Errorf("failed to build kubeconfig: %w", err)
		}
	}
	
	// Create network topology client
	topologyClient, err := networktopologyclient.NewForConfig(config)
	if err != nil {
		return nil, fmt.Errorf("failed to create topology client: %w", err)
	}
	
	return &NetworkAwarePlugin{
		handle:         h,
		topologyClient: topologyClient,
		topologyName:   "komarov-network", // Default topology name
	}, nil
}

func main() {
	var kubeconfig string
	var masterURL string
	
	flag.StringVar(&kubeconfig, "kubeconfig", "", "Path to kubeconfig file")
	flag.StringVar(&masterURL, "master", "", "Master URL")
	
	klog.InitFlags(nil)
	flag.Parse()
	
	ctx := context.Background()
	
	// Build Kubernetes config
	var config *rest.Config
	var err error
	
	if kubeconfig != "" {
		config, err = clientcmd.BuildConfigFromFlags(masterURL, kubeconfig)
	} else {
		config, err = rest.InClusterConfig()
	}
	
	if err != nil {
		klog.Fatal("Failed to create Kubernetes config: ", err)
	}
	
	// Create Kubernetes client
	kubeClient, err := kubernetes.NewForConfig(config)
	if err != nil {
		klog.Fatal("Failed to create Kubernetes client: ", err)
	}
	
	// Create informer factory
	informerFactory := informers.NewSharedInformerFactory(kubeClient, 0)
	
	// Register our plugin
	registry := frameworkruntime.Registry{
		"NetworkAware": New,
	}
	
	// Create scheduler configuration
	cfg := &scheduler.Config{
		ComponentConfig: schedulerapi.KubeSchedulerConfiguration{
			Profiles: []schedulerapi.KubeSchedulerProfile{
				{
					SchedulerName: SchedulerName,
					Plugins: &schedulerapi.Plugins{
						Filter: schedulerapi.PluginSet{
							Enabled: []schedulerapi.Plugin{
								{Name: "NetworkAware"},
								{Name: "NodeResourcesFit"},
								{Name: "NodeAffinity"},
							},
						},
						Score: schedulerapi.PluginSet{
							Enabled: []schedulerapi.Plugin{
								{Name: "NetworkAware"},
								{Name: "NodeResourcesFit"},
								{Name: "NodeAffinity"},
							},
						},
						Bind: schedulerapi.PluginSet{
							Enabled: []schedulerapi.Plugin{
								{Name: "DefaultBinder"},
							},
						},
					},
				},
			},
		},
		Client:            kubeClient,
		InformerFactory:   informerFactory,
		ComponentConfigVersion: "kubescheduler.config.k8s.io/v1beta3",
	}
	
	// Create and run scheduler
	sched, err := scheduler.New(
		kubeClient,
		informerFactory,
		scheduler.WithProfiles(cfg.ComponentConfig.Profiles...),
		scheduler.WithFrameworkOutOfTreeRegistry(registry),
	)
	
	if err != nil {
		klog.Fatal("Failed to create scheduler: ", err)
	}
	
	klog.InfoS("Starting network-aware scheduler", "name", SchedulerName)
	
	// Start informers
	informerFactory.Start(ctx.Done())
	informerFactory.WaitForCacheSync(ctx.Done())
	
	// Run scheduler
	sched.Run(ctx)
}