import sys
import argparse

import logging
import time
import threading

from kubernetes import client, config

from app import app


# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# TASK-3 - Health Checking K8s API server
def check_k8s_api_health(api_client):
    """
    Periodically checks and logs the K8s api server health.
    """
    while True:
        try:
            version = app.get_kubernetes_version(api_client)
            logger.info("Kubernetes API server is healthy. Version: %s", version)
        except Exception as e:
            logger.error("Kubernetes API server health check failed: %s", e)
        time.sleep(5) #checks every 5s.

# TASK-1 - Checking deployment available replica count are machted with desired replica defined in spec. 
def check_deployment_replicas(api_client):
    """
    Check the replicas health of deployment in the cluster in all the namespaces 
    """

    appsv1 = client.AppsV1Api(api_client)

    deployment_list = appsv1.list_deployment_for_all_namespaces().items

    all_deployments_healthy = True

    for deployment in deployment_list:
        name = deployment.metadata.name
        namespace = deployment.metadata.namespace
        desired_replicas = deployment.spec.replicas
        available_replicas = deployment.status.available_replicas

        if available_replicas is None:
            available_replicas = 0

        if desired_replicas != available_replicas:
            logger.warning(f"Deployment {name} in namespace {namespace} is not healthy.")
            logger.warning(f"Desired replicas: {desired_replicas}, Available replicas: {available_replicas}")
            all_deployments_healthy = False
        #else:
        #    logger.info(f"Deployment {name} in namespace {namespace} is healthy. Desired replicas: {desired_replicas}, Available replicas: {available_replicas}")

    if all_deployments_healthy:
        logger.info("All deployments are healthy.")
    else:
        logger.warning("Some deployments are not healthy.")


def periodic_deployment_replica_check(api_client, interval=60):
    while True:
        check_deployment_replicas(api_client)
        time.sleep(interval)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Tyk SRE Assignment",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("-k", "--kubeconfig", type=str, default="",
                        help="path to kubeconfig, leave empty for in-cluster")
    parser.add_argument("-a", "--address", type=str, default=":8080",
                        help="HTTP server listen address")
    #parser.add_argument("--check-deployments", action="store_true",
    #                    help="Check the health of all deployments")
    args = parser.parse_args()

    if args.kubeconfig != "":
        config.load_kube_config(config_file=args.kubeconfig)
    else:
        config.load_incluster_config()

    api_client = client.ApiClient()

    try:
        version = app.get_kubernetes_version(api_client)
    except Exception as e:
        print(e)
        sys.exit(1)

    print("Connected to Kubernetes {}".format(version))

    # the Kubernetes API server health check thread
    health_check_thread = threading.Thread(target=check_k8s_api_health, args=(api_client,))
    health_check_thread.daemon = True
    health_check_thread.start()

    # the deployment health check thread
    deployment_replica_count_check = threading.Thread(target=periodic_deployment_replica_check, args=(api_client,))
    deployment_replica_count_check.daemon = True
    deployment_replica_count_check.start()

    #if args.check_deployments:
    #    check_deployment_replicas(api_client)

    try:
        app.start_server(args.address)
    except KeyboardInterrupt:
        print("Server terminated")
