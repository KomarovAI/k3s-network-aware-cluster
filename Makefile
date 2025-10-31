.PHONY: help build test deploy clean install-master install-worker push

help:
	@echo "K3S Network-Aware Cluster - Make commands"
	@echo ""
	@echo "Usage:"
	@echo "  make build           Build all Docker images"
	@echo "  make test            Run tests"
	@echo "  make deploy          Deploy to K3S cluster"
	@echo "  make clean           Clean build artifacts"
	@echo "  make install-master  Install K3S master node"
	@echo "  make install-worker  Install K3S worker node"
	@echo "  make push            Push images to Docker Hub"

build:
	@echo "🏗️  Building Docker images..."
	docker build -t komarovai/network-aware-scheduler:latest -f docker/network-scheduler/Dockerfile .
	docker build -t komarovai/network-controller:latest -f docker/network-controller/Dockerfile .
	@echo "✅ All images built successfully!"

test:
	@echo "🧪 Running tests..."
	cd scheduler/network-aware-scheduler && go test -v ./...
	cd scheduler/network-controller && go test -v ./...
	@echo "✅ All tests passed!"

deploy:
	@echo "🚀 Deploying to K3S..."
	./scripts/deploy-cluster.sh
	@echo "✅ Deployment complete!"

clean:
	@echo "🧹 Cleaning build artifacts..."
	docker rmi komarovai/network-aware-scheduler:latest || true
	docker rmi komarovai/network-controller:latest || true
	@echo "✅ Cleanup complete!"

install-master:
	@echo "🎯 Installing K3S master..."
	./scripts/install-master.sh

install-worker:
	@echo "⚙️  Installing K3S worker..."
	./scripts/install-worker.sh

push:
	@echo "📤 Pushing images to Docker Hub..."
	docker push komarovai/network-aware-scheduler:latest
	docker push komarovai/network-controller:latest
	@echo "✅ Images pushed successfully!"

# Development helpers
dev-setup:
	@echo "🛠️  Setting up development environment..."
	go mod download -C scheduler/network-aware-scheduler
	go mod download -C scheduler/network-controller
	@echo "✅ Development environment ready!"

dev-build:
	@echo "🔨 Building Go binaries..."
	cd scheduler/network-aware-scheduler && go build -o ../../bin/network-scheduler .
	cd scheduler/network-controller && go build -o ../../bin/network-controller .
	@echo "✅ Binaries built in bin/ directory!"

check:
	@echo "🔍 Running code checks..."
	cd scheduler/network-aware-scheduler && go vet ./...
	cd scheduler/network-controller && go vet ./...
	cd scheduler/network-aware-scheduler && go fmt ./...
	cd scheduler/network-controller && go fmt ./...
	@echo "✅ Code checks passed!"

# Local development with kind
kind-create:
	@echo "🐳 Creating kind cluster..."
	kind create cluster --name network-aware --config kind-config.yaml

kind-delete:
	@echo "🗑️  Deleting kind cluster..."
	kind delete cluster --name network-aware

kind-load:
	@echo "📦 Loading images to kind cluster..."
	kind load docker-image komarovai/network-aware-scheduler:latest --name network-aware
	kind load docker-image komarovai/network-controller:latest --name network-aware