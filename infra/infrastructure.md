# Infrastructure Setup - Web Scraper Backend

## Overview

This document provides complete setup instructions for the Web Scraper Backend infrastructure on Google Cloud Platform, including load balancer configuration, health checks, and backend services.

## Initial Setup - Complete Command Reference

### 1. Firewall Rule for Health Checks

Check all firewall rules
```
gcloud compute firewall-rules list
```

If you want to run flask on port 5001 or any other and it is in the firewall rules list then you dont have to create new rule.
If desired port is not in the list, create a firewall rule to allow Google Cloud Load Balancer health checks to reach the backend instances:

```bash
# First check firewall rules list, if you required rule is there
gcloud compute firewall-rules list

# Create firewall rule for load balancer health checks
gcloud compute firewall-rules create allow-flask-5001 \
  --network=default \
  --action=ALLOW \
  --direction=INGRESS \
  --source-ranges=35.191.0.0/16,130.211.0.0/22 \
  --rules=tcp:5001 \
  --target-tags=hashtaglocal-backend \
  --description="Allow GCP Load Balancer health checks to web scraper on port 5001"
  ```

**Note**: Source ranges `35.191.0.0/16` and `130.211.0.0/22` are Google Cloud's health check IP ranges.

### 2. Instance Group Setup

Create an unmanaged instance group to contain the backend VM:

```bash
# Create unmanaged instance group
gcloud compute instance-groups unmanaged create webscraper-staging-group \
  --zone=us-central1-f \
  --description="Instance group for web scraping operations"

# Add the VM instance to the group
gcloud compute instance-groups unmanaged add-instances webscraper-staging-group \
  --zone=us-central1-f \
  --instances=staging-instance

# Set named port for the instance group
gcloud compute instance-groups unmanaged set-named-ports webscraper-staging-group \
  --zone=us-central1-f \
  --named-ports=http:5001

# Verify instance group
gcloud compute instance-groups unmanaged describe webscraper-instance-group \
  --zone=us-central1-f
```

### 3. Health Check Configuration

Create a health check to monitor the backend application:

```bash
# Create HTTP health check
gcloud compute health-checks create http webscraper-health-check \
  --port=5001 \
  --request-path=/api/health \
  --check-interval=10s \
  --timeout=5s \
  --unhealthy-threshold=2 \
  --healthy-threshold=2 \
  --description="Health check for web scraper operations"

# Verify health check
gcloud compute health-checks describe webscraper-health-check
```

### 4. Backend Service Creation

Create the backend service that connects the instance group with the load balancer:

```bash
# Create backend service
gcloud compute backend-services create webscraper-staging-backend \
  --protocol=HTTP \
  --port-name=http \
  --health-checks=webscraper-health-check \
  --global \
  --load-balancing-scheme=EXTERNAL_MANAGED \
  --timeout=30s \
  --description="Backend service for web scraper operations"

# Add the instance group as a backend
gcloud compute backend-services add-backend webscraper-staging-backend \
  --instance-group=webscraper-staging-group \
  --instance-group-zone=us-central1-f \
  --balancing-mode=UTILIZATION \
  --max-utilization=0.8 \
  --global

# Verify backend service
gcloud compute backend-services describe webscraper-staging-backend --global

# Check backend health
gcloud compute backend-services get-health webscraper-staging-backend --global
```

### 5. Load Balancer URL Map Update

Update the existing load balancer URL map to route traffic to the new backend:

```bash
# Export current URL map for backup
gcloud compute url-maps export https-staging \
  --destination=staging-urlmap-backup.yaml \
  --global

# Create updated URL map configuration (staging-urlmap-updated.yaml)
# See the Configuration section below for the YAML structure

# Update the URL map
gcloud compute url-maps import https-staging \
  --source=staging-urlmap-updated.yaml \
  --global

# Verify URL map
gcloud compute url-maps describe https-staging --global
```

## Load Balancer Configuration Details

### URL Map Path Routing with Rewrite

The URL map is configured to route `/webscrapestaging/*` requests to the webscraper-staging-backend while stripping the `/scrap` prefix:

```yaml
hostRules:
- hosts:
  - '*'
  pathMatcher: path-matcher-1
id: 6114781977877706469
kind: compute#urlMap
name: https-staging
pathMatchers:
- defaultService: https://www.googleapis.com/compute/v1/projects/ai-agent-boilerplate0/global/backendServices/staging-backend
  name: path-matcher-1
  routeRules:
  - matchRules:
    - prefixMatch: /local/
    priority: 1
    routeAction:
      urlRewrite:
        pathPrefixRewrite: /
      weightedBackendServices:
      - backendService: https://www.googleapis.com/compute/v1/projects/ai-agent-boilerplate0/global/backendServices/hashtaglocal-backend
        weight: 100
  - matchRules:
    - prefixMatch: /localstaging/
    priority: 2
    routeAction:
      urlRewrite:
        pathPrefixRewrite: /
      weightedBackendServices:
      - backendService: https://www.googleapis.com/compute/v1/projects/ai-agent-boilerplate0/global/backendServices/hashtaglocal-staging-backend
        weight: 100
  - matchRules:
    - prefixMatch: /webscrapestaging/
    priority: 3
    routeAction:
      urlRewrite:
        pathPrefixRewrite: /
      weightedBackendServices:
      - backendService: https://www.googleapis.com/compute/v1/projects/ai-agent-boilerplate0/global/backendServices/webscraper-staging-backend
        weight: 100
selfLink: https://www.googleapis.com/compute/v1/projects/ai-agent-boilerplate0/global/urlMaps/https-staging
```

### Test Health Check Endpoint

```bash
# Test via load balancer
curl https://staging.api.smalltech.in/webscrapestaging/api/health

# Expected response:
{
  "status": "ok",
  "message": "Service is running"
}
