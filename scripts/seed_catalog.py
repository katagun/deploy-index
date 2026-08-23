#!/usr/bin/env python3
"""Bootstrap the initial DeployIndex catalog.

This file is intentionally explicit and dependency-free. It is a starting inventory,
not a claim that every field has been independently verified. The weekly research
workflow turns seeded records into sourced, reviewed records over time.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "catalog" / "providers.json"

CATEGORY_LABELS = {
    "hyperscale-cloud": "Hyperscale cloud",
    "cloud-vps": "Cloud & VPS",
    "paas": "Application PaaS",
    "managed-containers": "Managed containers",
    "serverless-functions": "Serverless functions",
    "edge-compute": "Edge compute",
    "frontend-hosting": "Frontend hosting",
    "static-hosting": "Static hosting",
    "byoc-platform": "Bring your own cloud",
    "self-hosted-paas": "Self-hosted PaaS",
    "gpu-ai-cloud": "GPU & AI cloud",
    "backend-platform": "Backend platform",
    "database-platform": "Database platform",
    "bare-metal": "Bare metal",
    "managed-kubernetes": "Managed Kubernetes",
    "managed-wordpress": "Managed web & WordPress",
    "developer-sandbox": "Developer & agent sandbox",
    "game-hosting": "Game hosting",
    "decentralized-hosting": "Decentralized hosting",
}

DEFAULT_BEST_FOR = {
    "hyperscale-cloud": "Broad infrastructure portfolios and organizations that need many managed services.",
    "cloud-vps": "General-purpose virtual machines, predictable servers, and infrastructure building blocks.",
    "paas": "Deploying applications without operating most of the underlying infrastructure.",
    "managed-containers": "Running containerized services with managed scheduling, networking, and scaling.",
    "serverless-functions": "Event-driven code and workloads that benefit from usage-based scaling.",
    "edge-compute": "Latency-sensitive request processing and globally distributed application logic.",
    "frontend-hosting": "Frontend frameworks, preview deployments, and full-stack web applications.",
    "static-hosting": "Fast global delivery of static sites, documentation, and generated frontends.",
    "byoc-platform": "PaaS ergonomics while keeping workloads and data inside your own cloud account.",
    "self-hosted-paas": "Owning the infrastructure while retaining a Git-to-deploy platform experience.",
    "gpu-ai-cloud": "Model inference, training, batch compute, and bursty GPU workloads.",
    "backend-platform": "Authentication, APIs, storage, realtime, and backend primitives without building them all.",
    "database-platform": "Managed data services with developer-oriented provisioning and operations.",
    "bare-metal": "Dedicated physical servers, high and predictable performance, and custom networking.",
    "managed-kubernetes": "Teams standardizing on Kubernetes without running the control plane themselves.",
    "managed-wordpress": "Managed CMS, agency, ecommerce, and conventional website hosting.",
    "developer-sandbox": "Secure disposable environments for development, generated code, and AI agents.",
    "game-hosting": "Realtime multiplayer servers, matchmaking, and geographically distributed sessions.",
    "decentralized-hosting": "Workloads designed around decentralized compute, storage, or Web3 networks.",
}

providers: list[dict[str, Any]] = []


def add(
    slug: str,
    name: str,
    url: str,
    primary: str,
    *,
    entity: str = "provider",
    categories: list[str] | None = None,
    capabilities: list[str] | None = None,
    models: list[str] | None = None,
    era: str = "established",
    status: str = "active",
    availability: str = "general",
    open_source: bool = False,
    parent: str | None = None,
    summary: str | None = None,
    best_for: str | None = None,
    launch_year: int | None = None,
    featured: bool = False,
    sources: list[str] | None = None,
) -> None:
    all_categories = [primary, *(categories or [])]
    all_categories = list(dict.fromkeys(all_categories))
    providers.append(
        {
            "slug": slug,
            "name": name,
            "url": url,
            "entity_type": entity,
            "parent_slug": parent,
            "primary_category": primary,
            "categories": all_categories,
            "capabilities": sorted(set(capabilities or [])),
            "operating_models": sorted(set(models or ["managed-cloud"])),
            "era": era,
            "status": status,
            "availability": availability,
            "open_source": open_source,
            "launch_year": launch_year,
            "featured": featured,
            "summary": summary
            or f"{name} is a {CATEGORY_LABELS[primary].lower()} option in the DeployIndex catalog.",
            "best_for": best_for or DEFAULT_BEST_FOR[primary],
            "source_urls": sources or [url],
            "last_verified": None,
            "confidence": "seed",
            "change_note": "Initial catalog seed; awaiting source-by-source verification.",
        }
    )


# ---------------------------------------------------------------------------
# Hyperscale and broad cloud providers
# ---------------------------------------------------------------------------
add("aws", "Amazon Web Services", "https://aws.amazon.com/", "hyperscale-cloud",
    categories=["cloud-vps", "managed-containers", "serverless-functions", "managed-kubernetes", "database-platform", "bare-metal"],
    capabilities=["virtual-machines", "containers", "functions", "managed-kubernetes", "databases", "object-storage", "gpu", "bare-metal", "private-networking"],
    summary="The largest broad-service public cloud, spanning infrastructure, managed platforms, data, AI, edge, and enterprise services.",
    best_for="Organizations that need the broadest service catalog, global reach, and deep enterprise integration.", launch_year=2006, featured=True)
add("azure", "Microsoft Azure", "https://azure.microsoft.com/", "hyperscale-cloud",
    categories=["cloud-vps", "managed-containers", "serverless-functions", "managed-kubernetes", "database-platform", "bare-metal"],
    capabilities=["virtual-machines", "containers", "functions", "managed-kubernetes", "databases", "object-storage", "gpu", "private-networking"],
    summary="Microsoft's global cloud platform with strong enterprise identity, hybrid, data, application, and AI services.",
    best_for="Microsoft-centered enterprises, hybrid environments, Entra ID integration, and regulated workloads.", launch_year=2010, featured=True)
add("google-cloud", "Google Cloud", "https://cloud.google.com/", "hyperscale-cloud",
    categories=["cloud-vps", "managed-containers", "serverless-functions", "managed-kubernetes", "database-platform"],
    capabilities=["virtual-machines", "containers", "functions", "managed-kubernetes", "databases", "object-storage", "gpu", "private-networking"],
    summary="Google's cloud platform, especially strong in data, Kubernetes, serverless containers, networking, and machine learning.",
    best_for="Data-intensive systems, Kubernetes, serverless containers, analytics, and AI workloads.", launch_year=2008, featured=True)
add("oracle-cloud", "Oracle Cloud Infrastructure", "https://www.oracle.com/cloud/", "hyperscale-cloud",
    categories=["cloud-vps", "managed-kubernetes", "database-platform", "bare-metal"],
    capabilities=["virtual-machines", "containers", "managed-kubernetes", "databases", "object-storage", "gpu", "bare-metal", "private-networking"],
    summary="Oracle's public cloud, combining high-performance infrastructure with Oracle database and enterprise application services.", launch_year=2016)
add("ibm-cloud", "IBM Cloud", "https://www.ibm.com/cloud", "hyperscale-cloud",
    categories=["cloud-vps", "managed-containers", "managed-kubernetes", "database-platform", "bare-metal"],
    capabilities=["virtual-machines", "containers", "functions", "managed-kubernetes", "databases", "bare-metal", "private-networking"],
    summary="Enterprise cloud with managed Kubernetes, bare metal, regulated-industry capabilities, and IBM software integration.", launch_year=2011)
add("alibaba-cloud", "Alibaba Cloud", "https://www.alibabacloud.com/", "hyperscale-cloud",
    categories=["cloud-vps", "managed-containers", "managed-kubernetes", "database-platform"],
    capabilities=["virtual-machines", "containers", "functions", "managed-kubernetes", "databases", "object-storage", "gpu"],
    summary="A broad global cloud platform with particularly strong reach and service depth across China and Asia.", launch_year=2009)
add("tencent-cloud", "Tencent Cloud", "https://www.tencentcloud.com/", "hyperscale-cloud",
    categories=["cloud-vps", "managed-containers", "managed-kubernetes", "database-platform"],
    capabilities=["virtual-machines", "containers", "functions", "managed-kubernetes", "databases", "object-storage", "gpu"],
    summary="Tencent's public cloud platform, with a large service portfolio and strong presence in Asia, media, and gaming.")
add("huawei-cloud", "Huawei Cloud", "https://www.huaweicloud.com/intl/en-us/", "hyperscale-cloud",
    categories=["cloud-vps", "managed-containers", "managed-kubernetes", "database-platform"],
    capabilities=["virtual-machines", "containers", "functions", "managed-kubernetes", "databases", "object-storage", "gpu"],
    summary="A broad cloud platform with infrastructure, data, AI, and enterprise services across many international regions.")
add("baidu-ai-cloud", "Baidu AI Cloud", "https://cloud.baidu.com/", "hyperscale-cloud",
    categories=["gpu-ai-cloud", "cloud-vps", "database-platform"],
    capabilities=["virtual-machines", "containers", "databases", "object-storage", "gpu"],
    summary="Baidu's cloud and AI platform, focused heavily on Chinese-market infrastructure, data, and artificial intelligence.")

# ---------------------------------------------------------------------------
# Independent cloud, VPS, bare-metal, and regional infrastructure providers
# ---------------------------------------------------------------------------
cloud_rows = [
    ("digitalocean", "DigitalOcean", "https://www.digitalocean.com/", "Modern developer cloud with VMs, managed databases, Kubernetes, object storage, and App Platform."),
    ("akamai-cloud", "Akamai Cloud / Linode", "https://www.linode.com/", "Developer-oriented cloud infrastructure operated by Akamai, formerly known primarily as Linode."),
    ("vultr", "Vultr", "https://www.vultr.com/", "Globally distributed cloud compute, bare metal, Kubernetes, storage, and GPU infrastructure."),
    ("hetzner-cloud", "Hetzner Cloud", "https://www.hetzner.com/cloud/", "Cost-efficient European cloud servers, dedicated servers, networking, and storage."),
    ("ovhcloud", "OVHcloud", "https://www.ovhcloud.com/", "European cloud, dedicated servers, managed platforms, storage, and sovereign-cloud options."),
    ("scaleway", "Scaleway", "https://www.scaleway.com/", "European cloud with instances, bare metal, containers, Kubernetes, serverless, data, and AI services."),
    ("upcloud", "UpCloud", "https://upcloud.com/", "European cloud infrastructure emphasizing predictable performance, managed databases, Kubernetes, and private cloud."),
    ("civo", "Civo", "https://www.civo.com/", "Developer cloud known for fast Kubernetes, VMs, databases, and a simple platform experience."),
    ("exoscale", "Exoscale", "https://www.exoscale.com/", "European cloud infrastructure with compute, Kubernetes, object storage, databases, and networking."),
    ("gcore-cloud", "Gcore Cloud", "https://gcore.com/cloud", "Global cloud and edge infrastructure spanning compute, Kubernetes, storage, CDN, and AI."),
    ("ionos-cloud", "IONOS Cloud", "https://cloud.ionos.com/", "European infrastructure cloud with compute, Kubernetes, databases, networking, and enterprise services."),
    ("leaseweb", "Leaseweb", "https://www.leaseweb.com/cloud", "Global hosting and infrastructure provider with public cloud, dedicated servers, CDN, and networking."),
    ("kamatera", "Kamatera", "https://www.kamatera.com/", "Configurable cloud servers and managed infrastructure across a distributed global footprint."),
    ("contabo", "Contabo", "https://contabo.com/", "Budget-oriented VPS, virtual dedicated servers, object storage, and bare-metal hosting."),
    ("cloudsigma", "CloudSigma", "https://www.cloudsigma.com/", "Flexible cloud servers with customizable CPU, memory, storage, and regional infrastructure."),
    ("atlantic-net", "Atlantic.Net", "https://www.atlantic.net/", "Cloud servers, dedicated hosting, managed services, and compliance-oriented infrastructure."),
    ("phoenixnap", "phoenixNAP", "https://phoenixnap.com/", "Bare metal cloud, colocation, storage, networking, and infrastructure automation."),
    ("latitude-sh", "Latitude.sh", "https://www.latitude.sh/", "Developer-focused global bare-metal cloud with API-driven provisioning and networking."),
    ("cherry-servers", "Cherry Servers", "https://www.cherryservers.com/", "European bare-metal and cloud infrastructure with API-driven deployment and GPU options."),
    ("aruba-cloud", "Aruba Cloud", "https://www.arubacloud.com/", "European cloud servers, private cloud, storage, backup, and data-center services."),
    ("clouding-io", "Clouding.io", "https://clouding.io/", "European virtual cloud servers with flexible resources and straightforward hourly billing."),
    ("dreamcompute", "DreamCompute", "https://www.dreamhost.com/cloud/computing/", "DreamHost's OpenStack-based cloud compute offering for virtual servers and object storage."),
    ("rackspace", "Rackspace Technology", "https://www.rackspace.com/cloud", "Managed multicloud, private cloud, hosting, and professional operations across major providers."),
    ("servers-com", "Servers.com", "https://www.servers.com/", "Dedicated servers, private cloud, networking, and global data-center infrastructure."),
    ("cloudscale-ch", "cloudscale.ch", "https://www.cloudscale.ch/", "Swiss cloud servers, Kubernetes, object storage, and infrastructure with a regional focus."),
    ("infomaniak-cloud", "Infomaniak Public Cloud", "https://www.infomaniak.com/en/hosting/public-cloud", "Swiss public cloud and hosting with an emphasis on European data location and sustainability."),
    ("openmetal", "OpenMetal", "https://openmetal.io/", "Hosted private cloud and bare-metal infrastructure built around OpenStack and Kubernetes."),
    ("packetframe", "Packetframe", "https://packetframe.com/", "API-oriented bare-metal and network infrastructure for performance-sensitive workloads."),
]
for slug, name, url, summary in cloud_rows:
    add(slug, name, url, "cloud-vps", categories=["bare-metal"] if slug in {"phoenixnap", "latitude-sh", "cherry-servers", "servers-com", "openmetal", "packetframe"} else [],
        capabilities=["virtual-machines", "object-storage", "private-networking"] + (["bare-metal"] if slug in {"ovhcloud", "vultr", "scaleway", "leaseweb", "phoenixnap", "latitude-sh", "cherry-servers", "servers-com", "openmetal", "packetframe"} else []),
        summary=summary, featured=slug in {"digitalocean", "akamai-cloud", "vultr", "hetzner-cloud", "ovhcloud", "scaleway"})

# ---------------------------------------------------------------------------
# General PaaS, managed application platforms, and BYOC products
# ---------------------------------------------------------------------------
add("heroku", "Heroku", "https://www.heroku.com/", "paas",
    capabilities=["git-deploy", "containers", "background-workers", "cron-jobs", "databases", "preview-environments"],
    summary="The defining Git-to-deploy PaaS, with buildpacks, add-ons, managed data services, pipelines, and review apps.",
    best_for="Teams that value mature PaaS conventions and a large ecosystem over the lowest infrastructure cost.", launch_year=2007, featured=True)
add("render", "Render", "https://render.com/", "paas",
    capabilities=["git-deploy", "containers", "background-workers", "cron-jobs", "databases", "static-sites", "private-networking", "preview-environments"],
    summary="A broad modern PaaS for web services, private services, workers, cron jobs, static sites, and managed data.", era="modern", launch_year=2018, featured=True)
add("railway", "Railway", "https://railway.com/", "paas",
    capabilities=["git-deploy", "containers", "background-workers", "cron-jobs", "databases", "persistent-storage", "private-networking", "preview-environments"],
    summary="A highly developer-friendly platform for deploying applications, workers, databases, queues, and multi-service projects.", era="modern", launch_year=2020, featured=True)
add("fly-io", "Fly.io", "https://fly.io/", "managed-containers",
    categories=["edge-compute", "paas"],
    capabilities=["containers", "virtual-machines", "tcp-udp", "persistent-storage", "private-networking", "autoscaling", "multi-region"],
    summary="A distributed application platform built around fast-launching Machines, OCI images, Anycast networking, and regional volumes.",
    best_for="Globally distributed long-running services, non-HTTP protocols, and teams comfortable designing around regional state.", era="modern", launch_year=2017, featured=True)
add("koyeb", "Koyeb", "https://www.koyeb.com/", "paas",
    categories=["managed-containers", "edge-compute", "gpu-ai-cloud"],
    capabilities=["git-deploy", "containers", "background-workers", "autoscaling", "scale-to-zero", "multi-region", "gpu", "private-networking"],
    summary="A global application platform for Git and container deployments, autoscaling services, workers, and GPU workloads.", era="modern", launch_year=2021, featured=True)
add("northflank", "Northflank", "https://northflank.com/", "paas",
    categories=["managed-containers", "byoc-platform", "gpu-ai-cloud", "database-platform"],
    capabilities=["git-deploy", "containers", "background-workers", "cron-jobs", "databases", "gpu", "private-networking", "preview-environments", "managed-kubernetes"],
    models=["managed-cloud", "bring-your-own-cloud"],
    summary="A comprehensive application platform covering builds, services, jobs, databases, release workflows, GPUs, and BYOC.", era="modern", launch_year=2020, featured=True)
add("platform-sh", "Platform.sh", "https://platform.sh/", "paas",
    capabilities=["git-deploy", "containers", "databases", "preview-environments", "private-networking"],
    summary="A mature enterprise application platform built around reproducible Git-driven environments and managed services.")
add("upsun", "Upsun", "https://upsun.com/", "paas",
    capabilities=["git-deploy", "containers", "databases", "preview-environments", "private-networking"],
    summary="A newer Platform.sh offering emphasizing self-service application environments, GitOps workflows, and managed infrastructure.", era="recent", launch_year=2024)
add("sevalla", "Sevalla", "https://sevalla.com/", "paas",
    capabilities=["git-deploy", "containers", "databases", "static-sites", "object-storage"],
    summary="Kinsta's developer platform for application hosting, managed databases, static sites, and object storage.", era="recent", launch_year=2024)
add("leapcell", "Leapcell", "https://leapcell.io/", "paas",
    categories=["serverless-functions"], capabilities=["git-deploy", "containers", "background-workers", "databases", "autoscaling", "scale-to-zero"],
    summary="A newer serverless-first application platform for web services, asynchronous workloads, and integrated data services.", era="recent", launch_year=2024)
add("sliplane", "Sliplane", "https://sliplane.io/", "paas",
    capabilities=["git-deploy", "containers", "persistent-storage", "databases", "background-workers"],
    models=["managed-cloud", "dedicated-server"],
    summary="A managed Docker platform that places multiple applications on dedicated servers for predictable pricing and control.", era="recent", launch_year=2024)
add("zeabur", "Zeabur", "https://zeabur.com/", "paas",
    categories=["byoc-platform"], capabilities=["git-deploy", "containers", "databases", "persistent-storage"],
    models=["managed-cloud", "bring-your-own-cloud", "dedicated-server"], status="transitioning",
    summary="A developer platform that evolved from shared PaaS hosting toward dedicated servers, BYOS infrastructure, and AI-assisted operations.", era="modern", launch_year=2022)
add("replit-deployments", "Replit Deployments", "https://replit.com/deployments", "paas", entity="product", parent="replit",
    categories=["frontend-hosting", "serverless-functions"], capabilities=["git-deploy", "autoscaling", "scale-to-zero", "cron-jobs", "databases", "static-sites"],
    summary="IDE-native application publishing with autoscale, reserved VM, static, and scheduled deployment modes.", era="modern", launch_year=2023)
add("shuttle", "Shuttle", "https://www.shuttle.dev/", "paas",
    capabilities=["git-deploy", "background-workers", "databases", "cron-jobs"],
    summary="A Rust-native cloud platform where applications declare and provision supporting infrastructure from code.", era="modern", launch_year=2022)
add("back4app-containers", "Back4App Containers", "https://www.back4app.com/container-as-a-service-caas", "managed-containers", entity="product", parent="back4app",
    capabilities=["git-deploy", "containers", "autoscaling", "persistent-storage", "preview-environments"],
    summary="Dockerfile-based container hosting integrated with Back4App's broader backend platform.", era="modern", launch_year=2023)
add("qoddi", "Qoddi", "https://qoddi.com/", "paas",
    categories=["gpu-ai-cloud"], capabilities=["git-deploy", "containers", "databases", "persistent-storage", "gpu"],
    summary="A smaller managed application platform for Git and container deployments, data services, storage, and GPU workloads.", era="modern")
add("code-capsules", "Code Capsules", "https://www.codecapsules.io/", "paas",
    capabilities=["git-deploy", "containers", "databases", "background-workers"],
    summary="A Git- and Docker-oriented PaaS for full-stack applications, APIs, workers, and databases.", era="modern", launch_year=2021)
add("adaptable", "Adaptable", "https://adaptable.io/", "paas",
    capabilities=["git-deploy", "containers", "databases"],
    summary="A lightweight Git-to-deploy platform for web applications and managed data services.", era="modern")
add("cloudtype", "Cloudtype", "https://cloudtype.io/", "paas",
    capabilities=["git-deploy", "containers", "databases", "background-workers"],
    summary="A developer-focused application platform with Git deployment, container workloads, and managed resources.", era="modern")
add("clever-cloud", "Clever Cloud", "https://www.clever-cloud.com/", "paas",
    capabilities=["git-deploy", "containers", "background-workers", "databases", "private-networking"],
    summary="A European PaaS for applications, add-ons, managed data, and enterprise deployment workflows.")
add("scalingo", "Scalingo", "https://scalingo.com/", "paas",
    capabilities=["git-deploy", "containers", "background-workers", "cron-jobs", "databases", "private-networking"],
    summary="A European Heroku-style PaaS with managed databases and regionally focused hosting.")
add("aptible", "Aptible", "https://www.aptible.com/", "paas",
    capabilities=["git-deploy", "containers", "databases", "private-networking"],
    summary="A security- and compliance-oriented application platform for regulated teams and sensitive workloads.")
add("cloud-66", "Cloud 66", "https://www.cloud66.com/", "byoc-platform",
    capabilities=["git-deploy", "containers", "managed-kubernetes", "private-networking"], models=["bring-your-own-cloud"],
    summary="A deployment and operations platform that runs applications and Kubernetes across infrastructure you control.")
add("hatchbox", "Hatchbox", "https://www.hatchbox.io/", "paas",
    capabilities=["git-deploy", "background-workers", "databases", "cron-jobs"], models=["bring-your-own-cloud", "dedicated-server"],
    summary="A Rails-focused deployment platform for servers and cloud accounts you control.")
add("laravel-cloud", "Laravel Cloud", "https://cloud.laravel.com/", "paas",
    capabilities=["git-deploy", "autoscaling", "scale-to-zero", "databases", "object-storage", "preview-environments", "cron-jobs", "background-workers"],
    summary="An integrated managed platform designed specifically for Laravel applications, data, queues, storage, and previews.", era="recent", launch_year=2025, featured=True)
add("engine-yard", "Engine Yard", "https://www.engineyard.com/", "paas",
    capabilities=["git-deploy", "containers", "databases", "background-workers"],
    summary="A long-running managed application platform historically centered on Ruby and operational support.")
add("elestio", "Elestio", "https://elest.io/", "paas",
    categories=["byoc-platform"], capabilities=["containers", "databases", "persistent-storage"], models=["managed-cloud", "bring-your-own-cloud", "dedicated-server"],
    summary="Managed hosting for open-source applications on dedicated infrastructure or customer-provided servers.", era="modern")
add("zerops", "Zerops", "https://zerops.io/", "paas",
    capabilities=["git-deploy", "containers", "background-workers", "databases", "object-storage", "persistent-storage", "private-networking"],
    summary="A European developer cloud built around isolated Linux containers, managed data services, storage, and private project networking.", era="recent", launch_year=2024)
add("apply-build", "Apply.Build", "https://apply.build/", "paas",
    capabilities=["git-deploy", "containers", "private-networking"],
    summary="A newer European PaaS emphasizing GitHub deployment, security controls, metrics, logs, and automated TLS.", era="recent")
add("diploi", "Diploi", "https://diploi.com/", "paas",
    categories=["developer-sandbox", "managed-kubernetes"], capabilities=["git-deploy", "containers", "preview-environments", "managed-kubernetes"],
    summary="A development-lifecycle platform combining cloud development environments, CI/CD, application hosting, and Kubernetes access.", era="recent", launch_year=2024)
add("granite-cloud", "Granite", "https://granite.so/", "paas",
    capabilities=["git-deploy", "containers", "databases", "object-storage"], availability="preview",
    summary="A newer cloud platform for source and Docker deployments, managed databases, object storage, and team workflows.", era="recent", launch_year=2025)
add("seenode", "Seenode", "https://seenode.com/", "paas",
    capabilities=["git-deploy", "containers", "databases", "autoscaling"], availability="preview",
    summary="An early-stage Git-based application and database deployment platform with integrated observability.", era="recent")
add("kuberns", "Kuberns", "https://kuberns.com/", "paas",
    categories=["byoc-platform"], capabilities=["git-deploy", "containers", "managed-kubernetes"], availability="preview",
    summary="An emerging AI-operated deployment and infrastructure platform for Git repositories and cloud environments.", era="recent", launch_year=2025)

# BYOC platforms
add("northflank-byoc", "Northflank BYOC", "https://northflank.com/product/bring-your-own-cloud", "byoc-platform", entity="product", parent="northflank",
    categories=["managed-kubernetes", "paas"], capabilities=["git-deploy", "containers", "databases", "gpu", "managed-kubernetes", "private-networking", "preview-environments"],
    models=["bring-your-own-cloud"], summary="Northflank's complete application platform deployed into customer-controlled cloud or Kubernetes infrastructure.", era="modern")
add("ravion", "Ravion", "https://www.ravion.com/", "byoc-platform",
    capabilities=["git-deploy", "containers", "private-networking", "infrastructure-as-code"], models=["bring-your-own-cloud"],
    summary="An AWS-focused application and infrastructure control plane using visible Terraform/OpenTofu plans and customer-owned resources.", era="recent", launch_year=2025, featured=True)
add("flightcontrol", "Flightcontrol", "https://www.flightcontrol.dev/", "byoc-platform",
    capabilities=["git-deploy", "containers", "background-workers", "databases", "private-networking"], models=["bring-your-own-cloud"], status="transitioning",
    summary="An AWS deployment platform transitioning toward Ravion while continuing to operate existing application workflows.", era="modern", launch_year=2021)
add("porter", "Porter", "https://www.porter.run/", "byoc-platform",
    categories=["managed-kubernetes", "paas"], capabilities=["git-deploy", "containers", "managed-kubernetes", "gpu", "private-networking"], models=["bring-your-own-cloud"],
    summary="A PaaS-like deployment platform that runs applications on Kubernetes and cloud infrastructure owned by the customer.", era="modern", launch_year=2020, featured=True)
add("qovery", "Qovery", "https://www.qovery.com/", "byoc-platform",
    categories=["managed-kubernetes", "paas"], capabilities=["git-deploy", "containers", "managed-kubernetes", "databases", "gpu", "preview-environments", "private-networking"], models=["bring-your-own-cloud"],
    summary="A developer and platform-engineering layer for deploying applications and managed resources across customer Kubernetes environments.", era="modern", launch_year=2020)
add("zeet", "Zeet", "https://zeet.co/", "byoc-platform",
    categories=["managed-kubernetes"], capabilities=["git-deploy", "containers", "managed-kubernetes", "private-networking"], models=["bring-your-own-cloud"],
    summary="A cloud deployment and infrastructure control plane operating across customer-owned accounts and clusters.", era="modern", launch_year=2020)
add("defang", "Defang", "https://defang.io/", "byoc-platform",
    capabilities=["containers", "git-deploy", "private-networking", "infrastructure-as-code"], models=["bring-your-own-cloud"], open_source=True,
    summary="A portable Docker Compose-to-cloud platform that provisions applications and supporting infrastructure in customer accounts.", era="modern", launch_year=2023, featured=True)
add("stacktape", "Stacktape", "https://stacktape.com/", "byoc-platform",
    categories=["serverless-functions", "managed-containers"], capabilities=["containers", "functions", "databases", "object-storage", "infrastructure-as-code"], models=["bring-your-own-cloud"], open_source=True,
    summary="A configuration-driven AWS platform combining infrastructure provisioning, deployment, logs, metrics, and developer workflows.", era="modern", launch_year=2022)
add("encore-cloud", "Encore Cloud", "https://encore.dev/", "byoc-platform",
    categories=["backend-platform"], capabilities=["git-deploy", "containers", "databases", "private-networking", "infrastructure-as-code"], models=["managed-cloud", "bring-your-own-cloud"], open_source=True,
    summary="A backend framework and cloud automation layer that derives infrastructure from application architecture and deploys it to managed or customer cloud.", era="modern", launch_year=2021)
add("nullstone", "Nullstone", "https://nullstone.io/", "byoc-platform",
    capabilities=["git-deploy", "containers", "preview-environments", "infrastructure-as-code"], models=["bring-your-own-cloud"],
    summary="An internal developer platform for self-service deployments, reusable infrastructure modules, environments, and organizational guardrails.", era="modern", launch_year=2020)
add("skyhook", "Skyhook", "https://www.skyhook.io/", "byoc-platform",
    categories=["managed-kubernetes"], capabilities=["git-deploy", "containers", "managed-kubernetes", "private-networking"], models=["bring-your-own-cloud"],
    summary="A newer PaaS-like control plane that deploys Kubernetes-based application infrastructure into customer cloud accounts.", era="modern", launch_year=2023)

# ---------------------------------------------------------------------------
# Managed container, serverless, and application products from broad clouds
# ---------------------------------------------------------------------------
add("digitalocean-app-platform", "DigitalOcean App Platform", "https://www.digitalocean.com/products/app-platform", "paas", entity="product", parent="digitalocean",
    capabilities=["git-deploy", "containers", "background-workers", "static-sites", "databases", "autoscaling"],
    summary="DigitalOcean's managed PaaS for source repositories, Docker images, APIs, workers, static sites, and multi-component applications.", era="modern", launch_year=2020)
add("google-cloud-run", "Google Cloud Run", "https://cloud.google.com/run", "managed-containers", entity="product", parent="google-cloud",
    categories=["serverless-functions"], capabilities=["containers", "autoscaling", "scale-to-zero", "cron-jobs", "background-workers", "private-networking"],
    summary="Google's serverless container platform for request-driven services, jobs, and functions with rapid autoscaling and scale-to-zero.", launch_year=2019, featured=True)
add("azure-container-apps", "Azure Container Apps", "https://azure.microsoft.com/products/container-apps", "managed-containers", entity="product", parent="azure",
    categories=["serverless-functions"], capabilities=["containers", "autoscaling", "scale-to-zero", "cron-jobs", "background-workers", "private-networking"],
    summary="Azure's serverless container platform using revisions, KEDA-based autoscaling, jobs, networking, and optional Dapr integration.", era="modern", launch_year=2022, featured=True)
add("aws-ecs-fargate", "Amazon ECS with Fargate", "https://aws.amazon.com/fargate/", "managed-containers", entity="product", parent="aws",
    capabilities=["containers", "autoscaling", "private-networking", "persistent-storage", "gpu"],
    summary="AWS container orchestration with serverless compute capacity through Fargate and deep integration with AWS networking and services.", launch_year=2017)
add("aws-ecs-express", "Amazon ECS Express Mode", "https://aws.amazon.com/ecs/express-mode/", "managed-containers", entity="product", parent="aws",
    capabilities=["containers", "autoscaling", "private-networking", "git-deploy"],
    summary="A simplified AWS path from a container image to an autoscaling ECS service with networking and HTTPS resources created automatically.", era="recent", launch_year=2025)
add("aws-elastic-beanstalk", "AWS Elastic Beanstalk", "https://aws.amazon.com/elasticbeanstalk/", "paas", entity="product", parent="aws",
    capabilities=["git-deploy", "containers", "autoscaling", "private-networking"],
    summary="AWS's long-running application PaaS for deploying source bundles or containers onto managed AWS infrastructure.", launch_year=2011)
add("aws-app-runner", "AWS App Runner", "https://aws.amazon.com/apprunner/", "managed-containers", entity="product", parent="aws",
    capabilities=["git-deploy", "containers", "autoscaling", "private-networking"], status="sunset", availability="existing-customers-only",
    summary="AWS's source- and image-to-service container product, now closed to new customers and no longer receiving new features.", era="modern", launch_year=2021)
add("google-app-engine", "Google App Engine", "https://cloud.google.com/appengine", "paas", entity="product", parent="google-cloud",
    capabilities=["git-deploy", "autoscaling", "scale-to-zero", "private-networking"],
    summary="Google's original managed application platform with standard and flexible runtime environments.", launch_year=2008)
add("azure-app-service", "Azure App Service", "https://azure.microsoft.com/products/app-service", "paas", entity="product", parent="azure",
    capabilities=["git-deploy", "containers", "autoscaling", "private-networking", "preview-environments"],
    summary="Azure's mature managed web application platform for source and container deployments across common frameworks.", launch_year=2012)
add("ibm-code-engine", "IBM Cloud Code Engine", "https://www.ibm.com/products/code-engine", "managed-containers", entity="product", parent="ibm-cloud",
    categories=["serverless-functions"], capabilities=["containers", "functions", "autoscaling", "scale-to-zero", "cron-jobs", "background-workers"],
    summary="IBM's managed serverless runtime for containerized applications, jobs, source code, and functions.", era="modern", launch_year=2021)
add("scaleway-serverless-containers", "Scaleway Serverless Containers", "https://www.scaleway.com/en/serverless-containers/", "managed-containers", entity="product", parent="scaleway",
    capabilities=["containers", "autoscaling", "scale-to-zero", "private-networking"],
    summary="A European serverless container runtime with scale-to-zero, private networking, and HTTP workload support.", era="modern", launch_year=2021)
add("oracle-container-instances", "OCI Container Instances", "https://www.oracle.com/cloud/cloud-native/container-instances/", "managed-containers", entity="product", parent="oracle-cloud",
    capabilities=["containers", "private-networking"],
    summary="Oracle's managed container execution product for running containers without administering virtual machines or Kubernetes.", era="modern")

# ---------------------------------------------------------------------------
# Frontend, static, edge, and function platforms
# ---------------------------------------------------------------------------
add("vercel", "Vercel", "https://vercel.com/", "frontend-hosting",
    categories=["serverless-functions", "static-hosting", "managed-containers"],
    capabilities=["git-deploy", "static-sites", "functions", "edge-runtime", "preview-environments", "autoscaling", "scale-to-zero", "containers"],
    summary="The leading frontend cloud for Next.js and modern web frameworks, with previews, functions, edge delivery, and HTTP container deployment.",
    best_for="Next.js and frontend-heavy products where preview deployments and framework integration are central.", era="modern", launch_year=2015, featured=True)
add("netlify", "Netlify", "https://www.netlify.com/", "frontend-hosting",
    categories=["serverless-functions", "static-hosting", "edge-compute"], capabilities=["git-deploy", "static-sites", "functions", "edge-runtime", "preview-environments", "background-workers"],
    summary="A mature frontend platform combining static delivery, serverless functions, edge functions, previews, forms, and build workflows.", launch_year=2014, featured=True)
add("cloudflare-pages", "Cloudflare Pages", "https://pages.cloudflare.com/", "frontend-hosting", entity="product", parent="cloudflare",
    categories=["static-hosting", "edge-compute"], capabilities=["git-deploy", "static-sites", "functions", "edge-runtime", "preview-environments"],
    summary="Cloudflare's Git-integrated static and full-stack frontend hosting product, closely integrated with Workers.", era="modern", launch_year=2021, featured=True)
add("cloudflare-workers", "Cloudflare Workers", "https://workers.cloudflare.com/", "edge-compute", entity="product", parent="cloudflare",
    categories=["serverless-functions", "backend-platform"], capabilities=["functions", "edge-runtime", "autoscaling", "scale-to-zero", "databases", "object-storage"],
    summary="A globally distributed serverless runtime integrated with Durable Objects, storage, queues, workflows, AI, and Cloudflare's network.", launch_year=2017, featured=True)
add("cloudflare-containers", "Cloudflare Containers", "https://developers.cloudflare.com/containers/", "managed-containers", entity="product", parent="cloudflare",
    categories=["edge-compute", "developer-sandbox"], capabilities=["containers", "autoscaling", "scale-to-zero", "edge-runtime"],
    summary="Worker-controlled Linux containers for custom runtimes, binaries, agent workloads, and compute that exceeds isolate-runtime constraints.", era="recent", launch_year=2025, featured=True)
add("cloudflare-sandbox", "Cloudflare Sandbox", "https://developers.cloudflare.com/sandbox/", "developer-sandbox", entity="product", parent="cloudflare",
    categories=["edge-compute"], capabilities=["containers", "scale-to-zero", "code-execution"],
    summary="Isolated container-based execution environments for running generated code and agent tasks from Cloudflare Workers.", era="recent", launch_year=2026)
add("bunny-magic-containers", "bunny Magic Containers", "https://bunny.net/magic-containers/", "managed-containers", entity="product", parent="bunny-net",
    categories=["edge-compute"], capabilities=["containers", "tcp-udp", "autoscaling", "persistent-storage", "multi-region", "private-networking"],
    summary="A globally distributed Docker container platform with Anycast networking, HTTP/TCP/UDP exposure, autoscaling, and volumes.", era="recent", launch_year=2025, featured=True)
add("bunny-edge-scripting", "bunny Edge Scripting", "https://bunny.net/edge-scripting/", "edge-compute", entity="product", parent="bunny-net",
    categories=["serverless-functions"], capabilities=["functions", "edge-runtime", "autoscaling"],
    summary="Programmable edge execution integrated with bunny.net's CDN and global network.")
add("deno-deploy", "Deno Deploy", "https://deno.com/deploy", "edge-compute",
    categories=["serverless-functions"], capabilities=["functions", "edge-runtime", "autoscaling", "scale-to-zero"],
    summary="A web-standard JavaScript and TypeScript runtime for globally distributed applications and APIs.", era="modern", launch_year=2021)
add("fastly-compute", "Fastly Compute", "https://www.fastly.com/products/edge-compute", "edge-compute", entity="product", parent="fastly",
    capabilities=["functions", "edge-runtime", "webassembly", "autoscaling"],
    summary="Fastly's strongly isolated edge compute platform centered on WebAssembly and programmable delivery.", era="modern", launch_year=2021)
add("akamai-edgeworkers", "Akamai EdgeWorkers", "https://www.akamai.com/products/serverless-computing-edgeworkers", "edge-compute", entity="product", parent="akamai-cloud",
    capabilities=["functions", "edge-runtime", "autoscaling"],
    summary="Akamai's serverless JavaScript execution platform for request processing on its global delivery network.")
add("wasmer-edge", "Wasmer Edge", "https://wasmer.io/products/edge", "edge-compute",
    capabilities=["webassembly", "edge-runtime", "autoscaling", "scale-to-zero"],
    summary="A WebAssembly and WASIX application platform for portable multi-language workloads at the edge.", era="modern", launch_year=2023)
add("akamai-functions", "Akamai Functions / Fermyon", "https://www.akamai.com/", "edge-compute", entity="product", parent="akamai-cloud",
    capabilities=["webassembly", "functions", "edge-runtime", "scale-to-zero"], status="transitioning",
    summary="Fermyon's Spin-based WebAssembly serverless technology transitioning into Akamai's edge platform after acquisition.", era="recent")
add("val-town", "Val Town", "https://www.val.town/", "serverless-functions",
    capabilities=["functions", "cron-jobs", "scale-to-zero", "git-deploy"],
    summary="A lightweight hosted JavaScript environment for small APIs, automations, scheduled jobs, and shareable server-side functions.", era="modern", launch_year=2022)
add("firebase-app-hosting", "Firebase App Hosting", "https://firebase.google.com/docs/app-hosting", "frontend-hosting", entity="product", parent="firebase",
    categories=["managed-containers"], capabilities=["git-deploy", "containers", "static-sites", "autoscaling", "preview-environments"],
    summary="Google's framework-oriented full-stack hosting product built on Firebase, Cloud Build, Cloud Run, and global delivery.", era="recent", launch_year=2024)
add("firebase-hosting", "Firebase Hosting", "https://firebase.google.com/products/hosting", "static-hosting", entity="product", parent="firebase",
    categories=["frontend-hosting"], capabilities=["git-deploy", "static-sites", "preview-environments"],
    summary="Google's global static and web-app hosting integrated with Firebase services and serverless backends.")
add("aws-amplify-hosting", "AWS Amplify Hosting", "https://aws.amazon.com/amplify/hosting/", "frontend-hosting", entity="product", parent="aws",
    categories=["static-hosting"], capabilities=["git-deploy", "static-sites", "functions", "preview-environments"],
    summary="AWS-managed frontend hosting and CI/CD for web frameworks, static sites, and Amplify backends.")
add("azure-static-web-apps", "Azure Static Web Apps", "https://azure.microsoft.com/products/app-service/static", "frontend-hosting", entity="product", parent="azure",
    categories=["static-hosting", "serverless-functions"], capabilities=["git-deploy", "static-sites", "functions", "preview-environments"],
    summary="Azure's globally distributed static frontend hosting with integrated APIs, authentication, and preview environments.", era="modern", launch_year=2021)
add("github-pages", "GitHub Pages", "https://pages.github.com/", "static-hosting", entity="product", parent="github",
    capabilities=["git-deploy", "static-sites"],
    summary="Repository-backed static site hosting for documentation, project pages, portfolios, and generated websites.")
add("gitlab-pages", "GitLab Pages", "https://docs.gitlab.com/user/project/pages/", "static-hosting", entity="product", parent="gitlab",
    capabilities=["git-deploy", "static-sites"],
    summary="Static site hosting driven by GitLab repositories and CI/CD pipelines.")
add("surge", "Surge", "https://surge.sh/", "static-hosting",
    capabilities=["static-sites", "cli-deploy"],
    summary="A simple command-line deployment service for static web projects and custom domains.")
add("neocities", "Neocities", "https://neocities.org/", "static-hosting",
    capabilities=["static-sites"],
    summary="Community-oriented static web hosting inspired by the personal web and simple hand-built sites.")
add("cloudcannon", "CloudCannon", "https://cloudcannon.com/", "frontend-hosting",
    categories=["static-hosting"], capabilities=["git-deploy", "static-sites", "preview-environments"],
    summary="A Git-based content management and hosting platform for static-site generators and agency workflows.")
add("appwrite-sites", "Appwrite Sites", "https://appwrite.io/products/sites", "frontend-hosting", entity="product", parent="appwrite",
    categories=["static-hosting", "backend-platform"], capabilities=["git-deploy", "static-sites", "functions", "preview-environments"],
    summary="Static and server-rendered site hosting integrated with Appwrite's open backend platform.", era="recent", launch_year=2025)
add("vercel-sandbox", "Vercel Sandbox", "https://vercel.com/docs/vercel-sandbox", "developer-sandbox", entity="product", parent="vercel",
    capabilities=["containers", "code-execution", "scale-to-zero"],
    summary="Ephemeral Linux environments for building, testing, previewing, and running generated or untrusted code.", era="recent")

# Functions
function_rows = [
    ("aws-lambda", "AWS Lambda", "https://aws.amazon.com/lambda/", "aws", "AWS's event-driven serverless function platform with broad service integrations and container image support."),
    ("azure-functions", "Azure Functions", "https://azure.microsoft.com/products/functions", "azure", "Azure's event-driven functions platform with multiple runtimes, triggers, and hosting plans."),
    ("google-cloud-functions", "Google Cloud Run functions", "https://cloud.google.com/functions", "google-cloud", "Google's function deployment experience, now aligned with the Cloud Run execution foundation."),
    ("netlify-functions", "Netlify Functions", "https://www.netlify.com/platform/core/functions/", "netlify", "Serverless and background functions integrated with Netlify deployments and frontend workflows."),
    ("vercel-functions", "Vercel Functions", "https://vercel.com/docs/functions", "vercel", "Server-side functions integrated with Vercel projects, framework routing, previews, and Fluid Compute."),
    ("supabase-edge-functions", "Supabase Edge Functions", "https://supabase.com/edge-functions", "supabase", "Globally distributed TypeScript functions integrated with Supabase databases, authentication, and storage."),
    ("digitalocean-functions", "DigitalOcean Functions", "https://www.digitalocean.com/products/functions", "digitalocean", "DigitalOcean's managed serverless function runtime for event-driven code and APIs."),
]
for slug, name, url, parent, summary in function_rows:
    add(slug, name, url, "serverless-functions", entity="product", parent=parent,
        capabilities=["functions", "autoscaling", "scale-to-zero"], summary=summary,
        era="modern" if slug in {"supabase-edge-functions", "digitalocean-functions"} else "established")

# ---------------------------------------------------------------------------
# Self-hosted PaaS and open application platforms
# ---------------------------------------------------------------------------
selfhost_rows = [
    ("coolify", "Coolify", "https://coolify.io/", "A modern open-source, self-hostable alternative to Heroku, Netlify, and Vercel for applications, databases, and services.", 2021),
    ("dokploy", "Dokploy", "https://dokploy.com/", "An open-source deployment platform using Docker, Compose, Traefik, remote servers, databases, backups, and previews.", 2024),
    ("dokku", "Dokku", "https://dokku.com/", "A compact Docker-powered self-hosted PaaS that recreates core Heroku-style deployment workflows.", 2013),
    ("caprover", "CapRover", "https://caprover.com/", "A self-hosted application and database platform built around Docker and a web management interface.", 2017),
    ("kubero", "Kubero", "https://www.kubero.dev/", "A Kubernetes-native open-source PaaS supporting Git, Dockerfiles, buildpacks, jobs, autoscaling, and add-ons.", 2022),
    ("canine", "Canine", "https://canine.sh/", "A newer open-source Heroku-like application platform for Kubernetes and single-server K3s environments.", 2025),
    ("easypanel", "Easypanel", "https://easypanel.io/", "A modern server control panel for deploying applications, databases, and packaged services through Docker.", 2021),
    ("uncloud", "Uncloud", "https://uncloud.run/", "Multi-node Docker Compose deployment with WireGuard networking and HTTPS, without requiring Kubernetes or Swarm.", 2025),
    ("zaneops", "ZaneOps", "https://zaneops.dev/", "An open-source Docker Swarm PaaS with Git deployment, previews, blue-green releases, SSL, metrics, and logs.", 2025),
    ("tsuru", "Tsuru", "https://tsuru.io/", "An extensible open-source PaaS supporting multiple provisioners and application deployment workflows.", 2012),
    ("piku", "Piku", "https://piku.github.io/", "A tiny Git-push deployment platform inspired by Heroku and designed for small servers.", 2016),
    ("cloud-foundry", "Cloud Foundry", "https://www.cloudfoundry.org/", "A mature open-source enterprise application platform with buildpacks, routing, services, and multi-cloud implementations.", 2011),
    ("red-hat-openshift", "Red Hat OpenShift", "https://www.redhat.com/en/technologies/cloud-computing/openshift", "An enterprise Kubernetes application platform available as software and managed cloud services.", 2011),
    ("openfaas", "OpenFaaS", "https://www.openfaas.com/", "An open-source functions and container workload platform for Kubernetes and container infrastructure.", 2016),
    ("knative", "Knative", "https://knative.dev/", "Kubernetes components for serverless serving, eventing, autoscaling, revisions, and scale-to-zero.", 2018),
    ("apache-openwhisk", "Apache OpenWhisk", "https://openwhisk.apache.org/", "An open-source distributed serverless platform for event-driven functions and compositions.", 2016),
    ("fission", "Fission", "https://fission.io/", "A Kubernetes-native open-source serverless functions framework with multiple language environments.", 2016),
    ("nuclio", "Nuclio", "https://nuclio.io/", "A high-performance open-source serverless and event-processing framework for Kubernetes and edge systems.", 2017),
    ("temps", "Temps", "https://temps.sh/", "An early single-binary application platform combining deployment, databases, analytics, errors, replay, and monitoring.", 2026),
]
for slug, name, url, summary, year in selfhost_rows:
    add(slug, name, url, "self-hosted-paas", entity="project",
        categories=["managed-kubernetes"] if slug in {"kubero", "canine", "cloud-foundry", "red-hat-openshift", "openfaas", "knative", "apache-openwhisk", "fission", "nuclio"} else [],
        capabilities=["git-deploy", "containers", "self-hosted", "persistent-storage"] + (["managed-kubernetes"] if slug in {"kubero", "canine", "red-hat-openshift", "openfaas", "knative", "fission", "nuclio"} else []),
        models=["self-hosted"], open_source=True, summary=summary, launch_year=year,
        era="recent" if year >= 2024 else ("modern" if year >= 2020 else "established"),
        availability="preview" if slug == "temps" else "general", featured=slug in {"coolify", "dokploy", "uncloud"})

# ---------------------------------------------------------------------------
# GPU, AI, model inference, and agent infrastructure
# ---------------------------------------------------------------------------
add("modal", "Modal", "https://modal.com/", "gpu-ai-cloud",
    categories=["serverless-functions", "developer-sandbox"], capabilities=["functions", "gpu", "containers", "background-workers", "cron-jobs", "autoscaling", "scale-to-zero", "code-execution"],
    summary="A Python-first serverless compute platform for GPU inference, batch jobs, scheduled work, endpoints, and secure sandboxes.", era="modern", launch_year=2021, featured=True)
add("runpod", "RunPod", "https://www.runpod.io/", "gpu-ai-cloud",
    capabilities=["gpu", "containers", "autoscaling", "scale-to-zero", "persistent-storage"],
    summary="GPU pods, serverless GPU endpoints, clusters, and a broad marketplace of accelerator configurations.", era="modern", launch_year=2021, featured=True)
add("beam", "Beam", "https://www.beam.cloud/", "gpu-ai-cloud",
    categories=["serverless-functions"], capabilities=["gpu", "functions", "containers", "background-workers", "autoscaling", "scale-to-zero"],
    summary="A Python-first serverless GPU platform for inference endpoints, agents, task queues, training, and BYOC execution.", era="modern", launch_year=2022)
add("fal", "fal", "https://fal.ai/", "gpu-ai-cloud",
    capabilities=["gpu", "autoscaling", "scale-to-zero", "model-inference"],
    summary="A high-performance generative-media inference platform with hosted models, custom pipelines, and elastic GPU execution.", era="modern", launch_year=2021)
add("cerebrium", "Cerebrium", "https://www.cerebrium.ai/", "gpu-ai-cloud",
    capabilities=["gpu", "containers", "autoscaling", "scale-to-zero", "model-inference"],
    summary="A serverless GPU platform for low-latency inference, custom Python workloads, and region-aware deployment.", era="modern")
add("bentocloud", "BentoCloud", "https://www.bentoml.com/bento-cloud", "gpu-ai-cloud", entity="product", parent="bentoml",
    capabilities=["gpu", "containers", "autoscaling", "scale-to-zero", "model-inference"],
    summary="Managed deployment and scaling for AI services packaged with BentoML.", era="modern", launch_year=2023)
add("baseten", "Baseten", "https://www.baseten.co/", "gpu-ai-cloud",
    capabilities=["gpu", "containers", "autoscaling", "scale-to-zero", "model-inference"],
    summary="A production model inference platform for deploying, optimizing, scaling, and observing custom AI models.", era="modern")
add("replicate", "Replicate", "https://replicate.com/", "gpu-ai-cloud",
    capabilities=["gpu", "model-inference", "autoscaling", "scale-to-zero"],
    summary="A developer API and hosting platform for running community and custom machine-learning models.", era="modern")
add("together-ai", "Together AI", "https://www.together.ai/", "gpu-ai-cloud",
    capabilities=["gpu", "model-inference", "fine-tuning"],
    summary="An AI cloud for model inference, fine-tuning, and dedicated deployments across open and custom models.", era="modern")
add("fireworks-ai", "Fireworks AI", "https://fireworks.ai/", "gpu-ai-cloud",
    capabilities=["gpu", "model-inference", "fine-tuning"],
    summary="A managed platform for high-performance inference, fine-tuning, and deployment of language and multimodal models.", era="modern", launch_year=2022)
add("hugging-face-spaces", "Hugging Face Spaces", "https://huggingface.co/spaces", "gpu-ai-cloud", entity="product", parent="hugging-face",
    categories=["paas"], capabilities=["git-deploy", "containers", "gpu", "static-sites"],
    summary="Repository-backed hosting for machine-learning demos and applications using Gradio, Streamlit, Docker, and hardware upgrades.")
add("hugging-face-inference-endpoints", "Hugging Face Inference Endpoints", "https://huggingface.co/inference-endpoints", "gpu-ai-cloud", entity="product", parent="hugging-face",
    capabilities=["gpu", "containers", "autoscaling", "model-inference", "private-networking"],
    summary="Managed, autoscaling, and optionally private endpoints for deploying models from the Hugging Face ecosystem.")
add("lightning-ai", "Lightning AI", "https://lightning.ai/", "gpu-ai-cloud",
    categories=["developer-sandbox"], capabilities=["gpu", "containers", "code-execution", "model-inference"],
    summary="A cloud development and deployment platform for AI applications, training, studios, and inference services.", era="modern")
add("anyscale", "Anyscale", "https://www.anyscale.com/", "gpu-ai-cloud",
    capabilities=["gpu", "containers", "distributed-compute", "model-inference"],
    summary="A managed Ray platform for distributed Python, AI workloads, training, inference, and batch processing.", era="modern")
add("lambda-cloud", "Lambda Cloud", "https://lambda.ai/service/gpu-cloud", "gpu-ai-cloud", entity="product", parent="lambda",
    categories=["cloud-vps"], capabilities=["gpu", "virtual-machines", "persistent-storage"],
    summary="GPU cloud instances and clusters from Lambda for training, inference, and high-performance AI workloads.")
add("coreweave", "CoreWeave", "https://www.coreweave.com/", "gpu-ai-cloud",
    categories=["managed-kubernetes", "cloud-vps"], capabilities=["gpu", "containers", "managed-kubernetes", "object-storage", "private-networking"],
    summary="A specialized AI cloud providing large-scale GPU infrastructure, Kubernetes, storage, and high-performance networking.", era="modern", featured=True)
add("nebius", "Nebius", "https://nebius.com/", "gpu-ai-cloud",
    categories=["cloud-vps", "managed-kubernetes"], capabilities=["gpu", "virtual-machines", "containers", "managed-kubernetes", "object-storage"],
    summary="An AI-focused cloud platform offering GPU infrastructure, managed Kubernetes, storage, and data services.", era="recent", launch_year=2024)
add("crusoe-cloud", "Crusoe Cloud", "https://www.crusoe.ai/cloud", "gpu-ai-cloud",
    categories=["cloud-vps"], capabilities=["gpu", "virtual-machines", "containers", "managed-kubernetes"],
    summary="AI cloud infrastructure emphasizing large GPU clusters, high-performance networking, and energy-aware data centers.", era="modern")
add("paperspace", "Paperspace", "https://www.paperspace.com/", "gpu-ai-cloud", parent="digitalocean",
    capabilities=["gpu", "virtual-machines", "containers", "code-execution"],
    summary="GPU virtual machines, notebooks, and machine-learning development infrastructure now owned by DigitalOcean.")
add("genesis-cloud", "Genesis Cloud", "https://www.genesiscloud.com/", "gpu-ai-cloud",
    capabilities=["gpu", "virtual-machines", "persistent-storage", "private-networking"],
    summary="GPU cloud infrastructure positioned around cost-efficient accelerator instances and renewable-energy regions.")
add("fluidstack", "Fluidstack", "https://www.fluidstack.io/", "gpu-ai-cloud",
    categories=["bare-metal"], capabilities=["gpu", "bare-metal", "distributed-compute"],
    summary="Large-scale GPU clusters and AI infrastructure for training and inference workloads.")
add("vast-ai", "Vast.ai", "https://vast.ai/", "gpu-ai-cloud",
    capabilities=["gpu", "containers", "marketplace"], models=["marketplace"],
    summary="A marketplace for renting distributed GPU capacity using container-based workloads.")
add("cudo-compute", "CUDO Compute", "https://www.cudocompute.com/", "gpu-ai-cloud",
    capabilities=["gpu", "virtual-machines", "containers"],
    summary="GPU cloud compute for AI, rendering, and high-performance workloads across distributed infrastructure.")
add("salad", "Salad", "https://salad.com/", "gpu-ai-cloud",
    capabilities=["gpu", "containers", "distributed-compute", "autoscaling"],
    summary="A distributed cloud platform that runs containerized AI inference and batch workloads on consumer-grade GPU capacity.")
add("tensordock", "TensorDock", "https://www.tensordock.com/", "gpu-ai-cloud",
    capabilities=["gpu", "virtual-machines", "marketplace"], models=["marketplace"],
    summary="A marketplace-style GPU cloud offering virtual machines across independent data-center hosts.")

# Agent sandboxes and cloud development environments
sandbox_rows = [
    ("e2b", "E2B", "https://e2b.dev/", "Firecracker-based isolated sandboxes for AI-generated code, interpreters, and coding agents.", 2023),
    ("daytona", "Daytona", "https://www.daytona.io/", "Programmable, stateful, isolated development environments and agent sandboxes.", 2024),
    ("runloop", "Runloop", "https://runloop.ai/", "Secure cloud development environments and programmable sandboxes for coding agents.", 2024),
    ("gitpod", "Gitpod", "https://www.gitpod.io/", "Automated cloud development environments for repositories, teams, and standardized workspaces.", 2019),
    ("codesandbox", "CodeSandbox", "https://codesandbox.io/", "Cloud development environments, browser sandboxes, and isolated Devboxes for web projects.", 2017),
    ("ona", "Ona", "https://ona.com/", "A newer agentic development environment and cloud workspace platform evolving from Gitpod's team.", 2025),
    ("codespaces", "GitHub Codespaces", "https://github.com/features/codespaces", "GitHub-integrated cloud development environments backed by configurable containers.", 2020),
]
for slug, name, url, summary, year in sandbox_rows:
    add(slug, name, url, "developer-sandbox",
        capabilities=["containers", "code-execution", "persistent-storage"], summary=summary, launch_year=year,
        era="recent" if year >= 2024 else ("modern" if year >= 2020 else "established"), featured=slug in {"e2b", "daytona"})

# ---------------------------------------------------------------------------
# Backend-as-a-service and developer data platforms
# ---------------------------------------------------------------------------
backend_rows = [
    ("supabase", "Supabase", "https://supabase.com/", "Open-source PostgreSQL backend platform combining database, authentication, storage, realtime, functions, and APIs.", True, 2020),
    ("firebase", "Firebase", "https://firebase.google.com/", "Google's mobile and web backend platform for authentication, databases, storage, functions, analytics, and hosting.", False, 2011),
    ("appwrite", "Appwrite", "https://appwrite.io/", "Open-source backend platform providing authentication, databases, storage, functions, messaging, and site hosting.", True, 2019),
    ("convex", "Convex", "https://www.convex.dev/", "A reactive backend platform combining a database, server functions, synchronization, search, workflows, and storage.", True, 2021),
    ("nhost", "Nhost", "https://nhost.io/", "An open-source backend platform built around PostgreSQL, GraphQL, authentication, storage, and serverless functions.", True, 2019),
    ("hasura-cloud", "Hasura Cloud", "https://hasura.io/cloud", "Managed GraphQL and data API infrastructure for databases, services, permissions, and event-driven backends.", True, 2020),
    ("xano", "Xano", "https://www.xano.com/", "A visual backend platform for APIs, databases, authentication, workflows, and scalable application logic.", False, 2014),
    ("backendless", "Backendless", "https://backendless.com/", "A visual and code-based backend platform with data, users, APIs, messaging, and server-side logic.", False, 2012),
    ("back4app", "Back4App", "https://www.back4app.com/", "A managed Parse-based backend platform offering databases, authentication, APIs, functions, and container hosting.", True, 2015),
    ("pocketbase", "PocketBase", "https://pocketbase.io/", "A compact open-source backend in a single binary, combining an embedded database, auth, file storage, and realtime APIs.", True, 2022),
    ("parse-platform", "Parse Platform", "https://parseplatform.org/", "An open-source backend framework for data, users, files, cloud code, and push notifications.", True, 2011),
    ("amplify", "AWS Amplify", "https://aws.amazon.com/amplify/", "AWS's full-stack web and mobile development platform spanning hosting, data, authentication, storage, and APIs.", True, 2017),
]
for slug, name, url, summary, oss, year in backend_rows:
    add(slug, name, url, "backend-platform", capabilities=["databases", "authentication", "object-storage", "functions"],
        open_source=oss, summary=summary, launch_year=year,
        era="modern" if year >= 2020 else "established", featured=slug in {"supabase", "firebase", "appwrite", "convex"})

# Managed database platforms
db_rows = [
    ("neon", "Neon", "https://neon.com/", "Serverless PostgreSQL with branching, autoscaling, scale-to-zero, and developer-oriented integrations.", 2021),
    ("planetscale", "PlanetScale", "https://planetscale.com/", "A developer-focused managed relational database platform with branching workflows and scalable infrastructure.", 2018),
    ("turso", "Turso", "https://turso.tech/", "A developer data platform built around lightweight, distributed, and embedded database architecture.", 2022),
    ("cockroachdb-cloud", "CockroachDB Cloud", "https://www.cockroachlabs.com/product/cloud/", "Managed distributed SQL with resilient multi-region deployment and PostgreSQL-compatible access.", 2015),
    ("upstash", "Upstash", "https://upstash.com/", "Serverless Redis-compatible data, queues, messaging, vector search, and workflow products.", 2020),
    ("aiven", "Aiven", "https://aiven.io/", "Managed open-source data services across clouds, including PostgreSQL, Kafka, ClickHouse, and observability tools.", 2016),
    ("timescale-cloud", "Timescale Cloud", "https://www.timescale.com/cloud", "Managed PostgreSQL optimized for time-series, analytics, and high-ingest workloads.", 2017),
    ("mongodb-atlas", "MongoDB Atlas", "https://www.mongodb.com/atlas", "MongoDB's global managed database platform with search, vector, stream, and data services.", 2016),
    ("redis-cloud", "Redis Cloud", "https://redis.io/cloud/", "Managed Redis-compatible data services with global deployment, persistence, and advanced modules.", 2013),
    ("motherduck", "MotherDuck", "https://motherduck.com/", "A serverless analytics database built around DuckDB and collaborative cloud execution.", 2022),
    ("gel-cloud", "Gel Cloud", "https://www.geldata.com/cloud", "Managed database hosting for Gel, formerly EdgeDB, with a strongly typed data model and developer tooling.", 2023),
    ("prisma-postgres", "Prisma Postgres", "https://www.prisma.io/postgres", "A developer-oriented serverless PostgreSQL offering integrated with Prisma's ORM and data platform.", 2024),
    ("tembo", "Tembo", "https://tembo.io/", "A managed Postgres platform emphasizing extensions, workload-specific stacks, and developer control.", 2022),
    ("crunchy-bridge", "Crunchy Bridge", "https://www.crunchydata.com/products/crunchy-bridge", "Managed PostgreSQL from Crunchy Data across multiple cloud providers.", 2020),
    ("temporal-cloud", "Temporal Cloud", "https://temporal.io/cloud", "Managed durable execution infrastructure for reliable workflows, activities, retries, and long-running processes.", 2020),
    ("restate-cloud", "Restate Cloud", "https://restate.dev/cloud", "Managed durable execution and stateful service orchestration for reliable applications and agents.", 2024),
    ("dbos-cloud", "DBOS Cloud", "https://www.dbos.dev/", "A transactional application platform combining durable execution with database-backed workflow state.", 2024),
    ("golem-cloud", "Golem Cloud", "https://golem.cloud/", "A durable WebAssembly worker platform for long-lived stateful components and recoverable execution.", 2024),
    ("rivet-cloud", "Rivet Cloud", "https://www.rivet.dev/", "Stateful actors and durable realtime infrastructure for multiplayer, collaborative, and agent applications.", 2025),
]
for slug, name, url, summary, year in db_rows:
    add(slug, name, url, "database-platform", capabilities=["databases", "autoscaling"] + (["scale-to-zero"] if slug in {"neon", "upstash", "motherduck", "prisma-postgres"} else []),
        summary=summary, launch_year=year, era="recent" if year >= 2024 else ("modern" if year >= 2020 else "established"),
        featured=slug in {"neon", "planetscale", "turso", "upstash"})

# ---------------------------------------------------------------------------
# Managed Kubernetes products
# ---------------------------------------------------------------------------
k8s_rows = [
    ("amazon-eks", "Amazon EKS", "https://aws.amazon.com/eks/", "aws"),
    ("azure-aks", "Azure Kubernetes Service", "https://azure.microsoft.com/products/kubernetes-service", "azure"),
    ("google-gke", "Google Kubernetes Engine", "https://cloud.google.com/kubernetes-engine", "google-cloud"),
    ("digitalocean-kubernetes", "DigitalOcean Kubernetes", "https://www.digitalocean.com/products/kubernetes", "digitalocean"),
    ("linode-kubernetes", "Linode Kubernetes Engine", "https://www.linode.com/products/kubernetes/", "akamai-cloud"),
    ("vultr-kubernetes", "Vultr Kubernetes Engine", "https://www.vultr.com/products/kubernetes/", "vultr"),
    ("civo-kubernetes", "Civo Kubernetes", "https://www.civo.com/kubernetes", "civo"),
    ("scaleway-kapsule", "Scaleway Kapsule", "https://www.scaleway.com/en/kubernetes-kapsule/", "scaleway"),
    ("ovh-managed-kubernetes", "OVHcloud Managed Kubernetes", "https://www.ovhcloud.com/en/public-cloud/kubernetes/", "ovhcloud"),
    ("oracle-oke", "Oracle Kubernetes Engine", "https://www.oracle.com/cloud/cloud-native/container-engine-kubernetes/", "oracle-cloud"),
    ("ibm-kubernetes", "IBM Cloud Kubernetes Service", "https://www.ibm.com/products/kubernetes-service", "ibm-cloud"),
    ("alibaba-ack", "Alibaba Cloud ACK", "https://www.alibabacloud.com/product/kubernetes", "alibaba-cloud"),
]
for slug, name, url, parent in k8s_rows:
    add(slug, name, url, "managed-kubernetes", entity="product", parent=parent,
        capabilities=["managed-kubernetes", "containers", "private-networking", "autoscaling"],
        summary=f"{name} is the managed Kubernetes offering associated with {parent.replace('-', ' ').title()}.")

# ---------------------------------------------------------------------------
# Traditional managed web, CMS, and WordPress hosting
# ---------------------------------------------------------------------------
wp_rows = [
    ("wp-engine", "WP Engine", "https://wpengine.com/", "Managed WordPress and WooCommerce hosting with developer workflows, performance tooling, and agency features."),
    ("kinsta", "Kinsta", "https://kinsta.com/", "Managed WordPress hosting with performance, observability, staging, and agency-oriented workflows."),
    ("pantheon", "Pantheon", "https://pantheon.io/", "WebOps platform for WordPress and Drupal with multidev environments, workflows, and managed infrastructure."),
    ("acquia", "Acquia Cloud Platform", "https://www.acquia.com/products/drupal-cloud/cloud-platform", "Enterprise Drupal hosting, digital experience services, governance, and deployment workflows."),
    ("pressable", "Pressable", "https://pressable.com/", "Managed WordPress hosting from Automattic with staging, backups, security, and support."),
    ("wordpress-com", "WordPress.com", "https://wordpress.com/hosting/", "Hosted WordPress with plans ranging from managed websites to developer-oriented plugin and deployment capabilities."),
    ("cloudways", "Cloudways", "https://www.cloudways.com/", "Managed application and WordPress hosting layered over several infrastructure providers."),
    ("siteground", "SiteGround", "https://www.siteground.com/", "Managed web, WordPress, ecommerce, email, and shared hosting with developer tooling."),
    ("hostinger", "Hostinger", "https://www.hostinger.com/", "Large consumer and small-business host offering shared, cloud, VPS, website-builder, and WordPress plans."),
    ("dreamhost", "DreamHost", "https://www.dreamhost.com/", "Long-running web host with shared, WordPress, VPS, dedicated, and cloud offerings."),
    ("liquid-web", "Liquid Web", "https://www.liquidweb.com/", "Managed VPS, dedicated, cloud, and application hosting for business-critical websites and commerce."),
    ("nexcess", "Nexcess", "https://www.nexcess.net/", "Managed WordPress, WooCommerce, Magento, and ecommerce hosting from Liquid Web."),
    ("pagely", "Pagely", "https://pagely.com/", "Enterprise managed WordPress hosting with AWS-based infrastructure and operational support."),
    ("bluehost", "Bluehost", "https://www.bluehost.com/", "Mainstream shared, WordPress, ecommerce, and VPS hosting for individuals and small businesses."),
    ("a2-hosting", "A2 Hosting", "https://www.a2hosting.com/", "Shared, managed WordPress, VPS, dedicated, and reseller hosting."),
    ("greengeeks", "GreenGeeks", "https://www.greengeeks.com/", "Shared, WordPress, VPS, and reseller hosting with an environmental positioning."),
    ("hostgator", "HostGator", "https://www.hostgator.com/", "Shared, WordPress, VPS, dedicated, and reseller hosting for mainstream website workloads."),
    ("inmotion-hosting", "InMotion Hosting", "https://www.inmotionhosting.com/", "Shared, WordPress, VPS, dedicated, and managed hosting with business-oriented support."),
    ("namecheap-hosting", "Namecheap Hosting", "https://www.namecheap.com/hosting/", "Shared, WordPress, VPS, reseller, and dedicated hosting integrated with domain services."),
    ("godaddy-hosting", "GoDaddy Hosting", "https://www.godaddy.com/hosting/web-hosting", "Mass-market web, WordPress, VPS, and business hosting integrated with domains and site tools."),
]
for slug, name, url, summary in wp_rows:
    add(slug, name, url, "managed-wordpress", capabilities=["managed-cms", "staging", "backups"], summary=summary)

# ---------------------------------------------------------------------------
# Game hosting and realtime specialized platforms
# ---------------------------------------------------------------------------
game_rows = [
    ("hathora", "Hathora", "https://hathora.dev/", "A serverless platform for globally distributed multiplayer game servers and session orchestration.", 2021),
    ("edgegap", "Edgegap", "https://edgegap.com/", "Distributed game server orchestration and edge deployment for low-latency multiplayer sessions.", 2018),
    ("aws-gamelift", "Amazon GameLift Servers", "https://aws.amazon.com/gamelift/servers/", "AWS-managed dedicated game server hosting, matchmaking, fleets, and scaling.", 2016),
    ("azure-playfab", "Azure PlayFab", "https://playfab.com/", "Backend services, multiplayer servers, analytics, identity, and live operations for games.", 2014),
    ("heroic-cloud", "Heroic Cloud", "https://heroiclabs.com/heroic-cloud/", "Managed hosting and operations for Heroic Labs' Nakama realtime game and application server.", 2020),
    ("agones", "Agones", "https://agones.dev/", "An open-source Kubernetes platform for hosting, running, and scaling dedicated game servers.", 2017),
]
for slug, name, url, summary, year in game_rows:
    add(slug, name, url, "game-hosting", entity="project" if slug == "agones" else "product",
        capabilities=["containers", "autoscaling", "multi-region", "tcp-udp"], models=["self-hosted"] if slug == "agones" else ["managed-cloud"],
        open_source=slug == "agones", summary=summary, launch_year=year, era="modern" if year >= 2020 else "established")

# ---------------------------------------------------------------------------
# Decentralized and Web3-oriented hosting
# ---------------------------------------------------------------------------
decentral_rows = [
    ("akash-network", "Akash Network", "https://akash.network/", "A decentralized cloud marketplace for containerized compute capacity."),
    ("fleek", "Fleek", "https://fleek.xyz/", "Hosting and developer infrastructure for decentralized applications, edge services, and content networks."),
    ("spheron", "Spheron Network", "https://spheron.network/", "Decentralized compute and deployment infrastructure for applications and AI workloads."),
    ("flux", "Flux", "https://runonflux.com/", "A decentralized cloud network for applications, nodes, storage integrations, and distributed services."),
    ("internet-computer", "Internet Computer", "https://internetcomputer.org/", "A blockchain-based network for hosting canister applications, data, and web experiences on-chain."),
    ("arweave", "Arweave", "https://www.arweave.org/", "Permanent decentralized data storage used for immutable web content and application assets."),
]
for slug, name, url, summary in decentral_rows:
    add(slug, name, url, "decentralized-hosting", capabilities=["containers" if slug in {"akash-network", "flux", "spheron"} else "decentralized-storage"],
        models=["decentralized-network"], open_source=True, summary=summary, era="modern")

# ---------------------------------------------------------------------------
# Parent companies and broad developer platforms represented by products above
# ---------------------------------------------------------------------------
add("cloudflare", "Cloudflare", "https://www.cloudflare.com/", "edge-compute",
    categories=["frontend-hosting", "serverless-functions", "managed-containers", "backend-platform"],
    capabilities=["edge-runtime", "functions", "containers", "static-sites", "object-storage", "databases", "private-networking"],
    summary="A global connectivity and developer platform spanning CDN, security, Workers, storage, databases, queues, AI, containers, and hosting.", featured=True)
add("bunny-net", "bunny.net", "https://bunny.net/", "edge-compute",
    categories=["managed-containers", "static-hosting"], capabilities=["edge-runtime", "containers", "object-storage", "tcp-udp", "multi-region"],
    summary="A developer-friendly global edge platform for CDN, storage, DNS, media, scripting, logs, and distributed containers.")
add("fastly", "Fastly", "https://www.fastly.com/", "edge-compute",
    capabilities=["edge-runtime", "webassembly", "functions", "cdn"],
    summary="A programmable edge cloud for content delivery, security, observability, and WebAssembly-based compute.")
add("replit", "Replit", "https://replit.com/", "developer-sandbox",
    categories=["paas"], capabilities=["code-execution", "containers", "git-deploy", "databases", "static-sites"],
    summary="A browser- and AI-native software development environment with integrated application publishing and data services.", era="modern")
add("github", "GitHub", "https://github.com/", "developer-sandbox",
    categories=["static-hosting"], capabilities=["git-deploy", "code-execution", "static-sites", "ci-cd"],
    summary="The dominant Git collaboration platform, also providing Actions, Codespaces, package registries, and Pages hosting.")
add("gitlab", "GitLab", "https://gitlab.com/", "developer-sandbox",
    categories=["static-hosting"], capabilities=["git-deploy", "code-execution", "static-sites", "ci-cd"],
    summary="A DevSecOps platform combining Git repositories, CI/CD, security workflows, environments, packages, and Pages hosting.", open_source=True)
add("hugging-face", "Hugging Face", "https://huggingface.co/", "gpu-ai-cloud",
    categories=["paas"], capabilities=["model-inference", "gpu", "git-deploy", "containers"],
    summary="An open machine-learning platform and model ecosystem with repositories, Spaces, inference, training, and enterprise services.")
add("bentoml", "BentoML", "https://www.bentoml.com/", "gpu-ai-cloud", entity="project",
    capabilities=["containers", "model-inference", "gpu"], models=["self-hosted", "managed-cloud"], open_source=True,
    summary="An open-source framework and platform for packaging, serving, and deploying production AI inference services.")
add("lambda", "Lambda", "https://lambda.ai/", "gpu-ai-cloud",
    categories=["cloud-vps", "bare-metal"], capabilities=["gpu", "virtual-machines", "bare-metal", "distributed-compute"],
    summary="An AI infrastructure company offering GPU workstations, cloud instances, servers, and large training clusters.")

# ---------------------------------------------------------------------------
# Archived or historically important products retained for transparency
# ---------------------------------------------------------------------------
archived_rows = [
    ("cyclic", "Cyclic", "https://www.cyclic.sh/", "A former serverless full-stack hosting platform that discontinued hosting in 2024."),
    ("glitch-hosting", "Glitch Hosting", "https://glitch.com/", "Glitch's former application hosting service, retained as a historical directory entry after hosting was phased out."),
    ("edgio", "Edgio", "https://edg.io/", "A former edge and application delivery platform, previously Layer0, retained as a historical entry."),
    ("genezio-hosting", "Genezio Hosting", "https://genezio.com/", "The earlier general-purpose Genezio application hosting product before the company changed direction."),
    ("coherence", "Coherence", "https://www.withcoherence.com/", "A former developer platform for cloud environments and deployments, retained for historical transparency."),
]
for slug, name, url, summary in archived_rows:
    add(slug, name, url, "paas", status="archived", availability="discontinued",
        capabilities=["git-deploy"], summary=summary, era="modern")

# Validate uniqueness and write deterministic output.
slugs = [item["slug"] for item in providers]
if len(slugs) != len(set(slugs)):
    duplicates = sorted({slug for slug in slugs if slugs.count(slug) > 1})
    raise SystemExit(f"Duplicate slugs: {duplicates}")

providers.sort(key=lambda item: (item["name"].casefold(), item["slug"]))
payload = {
    "schema_version": 1,
    "catalog_name": "DeployIndex",
    "generated_on": date.today().isoformat(),
    "methodology": "Seed inventory. Entries become verified through reviewed weekly research proposals.",
    "category_labels": CATEGORY_LABELS,
    "providers": providers,
}
OUTPUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(f"Wrote {len(providers)} entries to {OUTPUT}")
