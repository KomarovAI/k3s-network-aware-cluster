package main

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"strconv"
	"strings"
	"time"

	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/client-go/kubernetes"
	"k8s.io/client-go/rest"
	"k8s.io/klog/v2"

	networktopologyv1 "github.com/KomarovAI/k3s-network-aware-cluster/pkg/apis/networktopology/v1"
	networktopologyclient "github.com/KomarovAI/k3s-network-aware-cluster/pkg/client/clientset/versioned"
)

const (
	DefaultUpdateInterval = 60 * time.Second
	DefaultTopologyName   = "komarov-network"
	MaxMeasurementRetries = 3
)

// NetworkController monitors and updates network topology
type NetworkController struct {
	kubeClient       kubernetes.Interface
	topologyClient   networktopologyclient.Interface
	topologyName     string
	updateInterval   time.Duration
	tailscaleNodes   map[string]string
}

// TailscaleStatus represents the output of 'tailscale status --json'
type TailscaleStatus struct {
	Peer map[string]TailscalePeer `json:"Peer"`
}

type TailscalePeer struct {
	HostName     string   `json:"HostName"`
	DNSName      string   `json:"DNSName"`
	TailscaleIPs []string `json:"TailscaleIPs"`
	Online       bool     `json:"Online"`
}

// NewNetworkController creates a new network controller
func NewNetworkController() (*NetworkController, error) {
	// Build Kubernetes config
	config, err := rest.InClusterConfig()
	if err != nil {
		klog.Warning("Failed to get in-cluster config, trying local kubeconfig")
		home := os.Getenv("HOME")
		if home == "" {
			return nil, fmt.Errorf("failed to get kubeconfig: %w", err)
		}
		kubeconfig := home + "/.kube/config"
		config, err = rest.InClusterConfigFromFlags("", kubeconfig)
		if err != nil {
			return nil, fmt.Errorf("failed to build kubeconfig: %w", err)
		}
	}

	// Create Kubernetes client
	kubeClient, err := kubernetes.NewForConfig(config)
	if err != nil {
		return nil, fmt.Errorf("failed to create kube client: %w", err)
	}

	// Create topology client
	topologyClient, err := networktopologyclient.NewForConfig(config)
	if err != nil {
		return nil, fmt.Errorf("failed to create topology client: %w", err)
	}

	return &NetworkController{
		kubeClient:     kubeClient,
		topologyClient: topologyClient,
		topologyName:   DefaultTopologyName,
		updateInterval: DefaultUpdateInterval,
		tailscaleNodes: make(map[string]string),
	}, nil
}

// Run starts the network controller
func (nc *NetworkController) Run(ctx context.Context) error {
	klog.InfoS("Starting network controller", "topology", nc.topologyName, "interval", nc.updateInterval)

	// Initial update
	if err := nc.updateNetworkTopology(ctx); err != nil {
		klog.ErrorS(err, "Failed initial network topology update")
	}

	// Periodic updates
	ticker := time.NewTicker(nc.updateInterval)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			klog.InfoS("Network controller stopped")
			return ctx.Err()
		case <-ticker.C:
			if err := nc.updateNetworkTopology(ctx); err != nil {
				klog.ErrorS(err, "Failed to update network topology")
			}
		}
	}
}

// updateNetworkTopology measures network characteristics and updates the CRD
func (nc *NetworkController) updateNetworkTopology(ctx context.Context) error {
	klog.V(2).InfoS("Updating network topology")

	// Get all cluster nodes
	nodes, err := nc.kubeClient.CoreV1().Nodes().List(ctx, metav1.ListOptions{})
	if err != nil {
		return fmt.Errorf("failed to list nodes: %w", err)
	}

	// Update Tailscale node mapping
	if err := nc.updateTailscaleNodes(); err != nil {
		klog.ErrorS(err, "Failed to update Tailscale nodes")
	}

	// Build topology
	topology := &networktopologyv1.NetworkTopology{
		ObjectMeta: metav1.ObjectMeta{
			Name: nc.topologyName,
		},
		Spec: networktopologyv1.NetworkTopologySpec{
			Nodes: make(map[string]networktopologyv1.NodeSpec),
		},
	}

	measurementCount := 0
	totalLatency := int64(0)
	totalBandwidth := int64(0)

	// Measure characteristics between all node pairs
	for _, sourceNode := range nodes.Items {
		nodeSpec := networktopologyv1.NodeSpec{
			Bandwidth: make(map[string]string),
			Latency:   make(map[string]string),
			Cost:      make(map[string]float64),
		}

		// Set node zone and capabilities
		if zone := sourceNode.Labels["zone"]; zone != "" {
			nodeSpec.Zone = zone
		}
		if region := sourceNode.Labels["region"]; region != "" {
			nodeSpec.Region = region
		}

		// Set capabilities based on labels
		var capabilities []string
		if sourceNode.Labels["gpu"] == "nvidia" {
			capabilities = append(capabilities, "gpu-direct")
		}
		if sourceNode.Labels["role"] == "public-gateway" {
			capabilities = append(capabilities, "internet")
		}
		if sourceNode.Labels["zone"] == "local" {
			capabilities = append(capabilities, "high-bandwidth", "low-latency")
		}
		nodeSpec.Capabilities = capabilities

		for _, targetNode := range nodes.Items {
			if sourceNode.Name == targetNode.Name {
				continue
			}

			// Get target node IP
			targetIP := nc.getNodeIP(&targetNode)
			if targetIP == "" {
				klog.V(3).InfoS("No IP found for target node", "source", sourceNode.Name, "target", targetNode.Name)
				continue
			}

			// Measure latency
			latency := nc.measureLatency(targetIP)
			nodeSpec.Latency[targetNode.Name] = fmt.Sprintf("%dms", latency)
			totalLatency += latency

			// Measure bandwidth (less frequently to avoid network congestion)
			bandwidth := nc.measureBandwidth(targetIP)
			nodeSpec.Bandwidth[targetNode.Name] = fmt.Sprintf("%dmbps", bandwidth)
			totalBandwidth += bandwidth

			// Calculate cost (inverse of bandwidth)
			cost := nc.calculateCost(bandwidth, latency)
			nodeSpec.Cost[targetNode.Name] = cost

			measurementCount++
			klog.V(4).InfoS("Measured network characteristics",
				"source", sourceNode.Name,
				"target", targetNode.Name,
				"latency", latency,
				"bandwidth", bandwidth,
				"cost", cost)
		}

		topology.Spec.Nodes[sourceNode.Name] = nodeSpec
	}

	// Set status
	now := metav1.Now()
	topology.Status = networktopologyv1.NetworkTopologyStatus{
		LastUpdated:      &now,
		NodeCount:        len(nodes.Items),
		MeasurementCount: measurementCount,
		HealthScore:      nc.calculateHealthScore(totalLatency, totalBandwidth, measurementCount),
		Conditions: []metav1.Condition{
			{
				Type:               "Ready",
				Status:             metav1.ConditionTrue,
				LastTransitionTime: now,
				Reason:             "MeasurementComplete",
				Message:            fmt.Sprintf("Successfully measured %d network connections", measurementCount),
			},
		},
	}

	// Create or update the topology CRD
	return nc.updateTopologyCRD(ctx, topology)
}

// updateTailscaleNodes updates the mapping of node names to Tailscale IPs
func (nc *NetworkController) updateTailscaleNodes() error {
	cmd := exec.Command("tailscale", "status", "--json")
	output, err := cmd.Output()
	if err != nil {
		return fmt.Errorf("failed to get tailscale status: %w", err)
	}

	var status TailscaleStatus
	if err := json.Unmarshal(output, &status); err != nil {
		return fmt.Errorf("failed to parse tailscale status: %w", err)
	}

	// Clear previous mapping
	nc.tailscaleNodes = make(map[string]string)

	// Build new mapping
	for _, peer := range status.Peer {
		if len(peer.TailscaleIPs) > 0 && peer.Online {
			hostname := strings.Split(peer.DNSName, ".")[0] // Extract hostname from FQDN
			nc.tailscaleNodes[hostname] = peer.TailscaleIPs[0]
			nc.tailscaleNodes[peer.HostName] = peer.TailscaleIPs[0]
		}
	}

	klog.V(3).InfoS("Updated Tailscale node mapping", "nodes", len(nc.tailscaleNodes))
	return nil
}

// getNodeIP returns the IP address for a node (Tailscale preferred, then internal)
func (nc *NetworkController) getNodeIP(node *metav1.Node) string {
	// Try Tailscale IP first
	if tailscaleIP, exists := nc.tailscaleNodes[node.Name]; exists {
		return tailscaleIP
	}

	// Fallback to node internal IP
	for _, addr := range node.Status.Addresses {
		if addr.Type == metav1.NodeInternalIP {
			return addr.Address
		}
	}

	return ""
}

// measureLatency measures network latency to a target IP
func (nc *NetworkController) measureLatency(targetIP string) int64 {
	for retry := 0; retry < MaxMeasurementRetries; retry++ {
		cmd := exec.Command("ping", "-c", "3", "-W", "2000", targetIP)
		output, err := cmd.Output()
		if err != nil {
			klog.V(4).InfoS("Ping failed", "target", targetIP, "attempt", retry+1, "error", err)
			continue
		}

		// Parse ping output
		lines := strings.Split(string(output), "\n")
		for _, line := range lines {
			if strings.Contains(line, "avg") {
				parts := strings.Split(line, "/")
				if len(parts) >= 5 {
					avgStr := strings.TrimSpace(parts[4])
					if avg, err := strconv.ParseFloat(avgStr, 64); err == nil {
						return int64(avg)
					}
				}
			}
		}
	}

	// Default high latency on failure
	klog.V(3).InfoS("Failed to measure latency, using default", "target", targetIP)
	return 1000
}

// measureBandwidth measures network bandwidth to a target IP
func (nc *NetworkController) measureBandwidth(targetIP string) int64 {
	// Check if iperf3 is available
	if _, err := exec.LookPath("iperf3"); err != nil {
		klog.V(3).InfoS("iperf3 not available, estimating bandwidth from ping")
		return nc.estimateBandwidthFromLatency(targetIP)
	}

	for retry := 0; retry < MaxMeasurementRetries; retry++ {
		// Try to connect to iperf3 server (assume it's running on port 5201)
		cmd := exec.Command("iperf3", "-c", targetIP, "-t", "3", "-f", "m", "-P", "1")
		output, err := cmd.Output()
		if err != nil {
			klog.V(4).InfoS("iperf3 failed", "target", targetIP, "attempt", retry+1, "error", err)
			continue
		}

		// Parse iperf3 output
		lines := strings.Split(string(output), "\n")
		for _, line := range lines {
			if strings.Contains(line, "sender") && strings.Contains(line, "Mbits/sec") {
				parts := strings.Fields(line)
				for i, part := range parts {
					if part == "Mbits/sec" && i > 0 {
						if bw, err := strconv.ParseFloat(parts[i-1], 64); err == nil {
							return int64(bw)
						}
					}
				}
			}
		}
	}

	// Fallback to estimation
	return nc.estimateBandwidthFromLatency(targetIP)
}

// estimateBandwidthFromLatency estimates bandwidth based on latency (rough approximation)
func (nc *NetworkController) estimateBandwidthFromLatency(targetIP string) int64 {
	latency := nc.measureLatency(targetIP)
	
	// Very rough estimation based on typical network characteristics
	switch {
	case latency < 5:  // Local network
		return 1000 // 1 Gbps
	case latency < 20: // Fast WAN
		return 100  // 100 Mbps
	case latency < 50: // Internet
		return 50   // 50 Mbps
	default:           // Slow/congested
		return 10   // 10 Mbps
	}
}

// calculateCost calculates the cost of data transfer based on bandwidth and latency
func (nc *NetworkController) calculateCost(bandwidth, latency int64) float64 {
	if bandwidth <= 0 {
		return 1.0 // Maximum cost
	}

	// Base cost inversely proportional to bandwidth
	baseCost := 1000.0 / float64(bandwidth)
	
	// Latency penalty
	latencyPenalty := float64(latency) / 100.0
	
	cost := baseCost + latencyPenalty
	
	// Normalize to 0.0-1.0 range
	if cost > 1.0 {
		cost = 1.0
	}
	if cost < 0.0 {
		cost = 0.0
	}
	
	return cost
}

// calculateHealthScore calculates overall network health score
func (nc *NetworkController) calculateHealthScore(totalLatency, totalBandwidth int64, measurementCount int) float64 {
	if measurementCount == 0 {
		return 0.0
	}

	avgLatency := float64(totalLatency) / float64(measurementCount)
	avgBandwidth := float64(totalBandwidth) / float64(measurementCount)

	// Score based on latency (lower is better)
	latencyScore := 1.0 - (avgLatency / 200.0) // 200ms = 0 score
	if latencyScore < 0 {
		latencyScore = 0
	}

	// Score based on bandwidth (higher is better)
	bandwidthScore := avgBandwidth / 1000.0 // 1Gbps = 1.0 score
	if bandwidthScore > 1 {
		bandwidthScore = 1
	}

	// Combined score (weighted average)
	healthScore := (latencyScore*0.4 + bandwidthScore*0.6)
	
	return healthScore
}

// updateTopologyCRD creates or updates the network topology CRD
func (nc *NetworkController) updateTopologyCRD(ctx context.Context, topology *networktopologyv1.NetworkTopology) error {
	// Try to get existing topology
	existing, err := nc.topologyClient.NetworkV1().NetworkTopologies().Get(ctx, nc.topologyName, metav1.GetOptions{})
	if err != nil {
		// Create new topology
		klog.InfoS("Creating new network topology", "name", nc.topologyName)
		_, err = nc.topologyClient.NetworkV1().NetworkTopologies().Create(ctx, topology, metav1.CreateOptions{})
		if err != nil {
			return fmt.Errorf("failed to create topology: %w", err)
		}
	} else {
		// Update existing topology
		topology.ResourceVersion = existing.ResourceVersion
		topology.ObjectMeta.UID = existing.ObjectMeta.UID
		
		klog.V(2).InfoS("Updating network topology", "name", nc.topologyName)
		_, err = nc.topologyClient.NetworkV1().NetworkTopologies().Update(ctx, topology, metav1.UpdateOptions{})
		if err != nil {
			return fmt.Errorf("failed to update topology: %w", err)
		}
	}

	klog.InfoS("Successfully updated network topology",
		"name", nc.topologyName,
		"nodes", topology.Status.NodeCount,
		"measurements", topology.Status.MeasurementCount,
		"health", topology.Status.HealthScore)

	return nil
}

func main() {
	klog.InitFlags(nil)

	ctx := context.Background()

	controller, err := NewNetworkController()
	if err != nil {
		klog.Fatal("Failed to create network controller: ", err)
	}

	if err := controller.Run(ctx); err != nil {
		klog.Fatal("Network controller failed: ", err)
	}
}