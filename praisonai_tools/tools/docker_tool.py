"""Docker Tool for PraisonAI Agents.

Manage Docker containers, images, and execute commands.

Usage:
    from praisonai_tools import DockerTool
    
    docker = DockerTool()
    
    # List containers
    containers = docker.list_containers()
    
    # Run a container
    result = docker.run_container("python:3.11", command="python --version")
    
    # Execute command in container
    output = docker.exec_command(container_id="abc123", command="ls -la")

Environment Variables:
    DOCKER_HOST: Docker daemon URL (optional, uses default socket)
"""

import os
import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class DockerTool(BaseTool):
    """Tool for managing Docker containers and images."""
    
    name = "docker"
    description = "Manage Docker containers - list, run, stop, and execute commands."
    
    def __init__(
        self,
        base_url: Optional[str] = None,
    ):
        """Initialize DockerTool.
        
        Args:
            base_url: Docker daemon URL (default: unix socket)
        """
        self.base_url = base_url or os.getenv("DOCKER_HOST")
        self._client = None
        super().__init__()
    
    @property
    def client(self):
        """Lazy-load Docker client."""
        if self._client is None:
            try:
                import docker
            except ImportError:
                raise ImportError("docker not installed. Install with: pip install docker")
            
            if self.base_url:
                self._client = docker.DockerClient(base_url=self.base_url)
            else:
                self._client = docker.from_env()
        return self._client
    
    def run(
        self,
        action: str = "list_containers",
        image: Optional[str] = None,
        container_id: Optional[str] = None,
        command: Optional[str] = None,
        **kwargs
    ) -> Union[str, Dict[str, Any], List[Dict[str, Any]]]:
        """Execute Docker action."""
        action = action.lower().replace("-", "_")
        
        if action == "list_containers":
            return self.list_containers(**kwargs)
        elif action == "list_images":
            return self.list_images()
        elif action == "run_container":
            return self.run_container(image=image, command=command, **kwargs)
        elif action == "stop_container":
            return self.stop_container(container_id=container_id)
        elif action == "remove_container":
            return self.remove_container(container_id=container_id)
        elif action == "exec_command":
            return self.exec_command(container_id=container_id, command=command)
        elif action == "logs":
            return self.get_logs(container_id=container_id, **kwargs)
        elif action == "pull_image":
            return self.pull_image(image=image)
        elif action == "info":
            return self.get_info()
        else:
            return {"error": f"Unknown action: {action}"}
    
    def list_containers(self, all_containers: bool = False) -> List[Dict[str, Any]]:
        """List Docker containers.
        
        Args:
            all_containers: Include stopped containers
            
        Returns:
            List of container info
        """
        try:
            containers = self.client.containers.list(all=all_containers)
            
            return [
                {
                    "id": c.short_id,
                    "name": c.name,
                    "image": c.image.tags[0] if c.image.tags else c.image.short_id,
                    "status": c.status,
                    "created": str(c.attrs.get("Created", "")),
                }
                for c in containers
            ]
        except Exception as e:
            logger.error(f"Docker list_containers error: {e}")
            return [{"error": str(e)}]
    
    def list_images(self) -> List[Dict[str, Any]]:
        """List Docker images.
        
        Returns:
            List of image info
        """
        try:
            images = self.client.images.list()
            
            return [
                {
                    "id": img.short_id,
                    "tags": img.tags,
                    "size": f"{img.attrs.get('Size', 0) / 1024 / 1024:.1f} MB",
                    "created": str(img.attrs.get("Created", "")),
                }
                for img in images
            ]
        except Exception as e:
            logger.error(f"Docker list_images error: {e}")
            return [{"error": str(e)}]
    
    def run_container(
        self,
        image: str,
        command: Optional[str] = None,
        name: Optional[str] = None,
        detach: bool = True,
        remove: bool = False,
        environment: Optional[Dict[str, str]] = None,
        ports: Optional[Dict[str, int]] = None,
        volumes: Optional[Dict[str, Dict]] = None,
    ) -> Dict[str, Any]:
        """Run a Docker container.
        
        Args:
            image: Image name/tag
            command: Command to run
            name: Container name
            detach: Run in background
            remove: Remove after exit
            environment: Environment variables
            ports: Port mappings {container_port: host_port}
            volumes: Volume mappings
            
        Returns:
            Container info or output
        """
        if not image:
            return {"error": "image is required"}
        
        try:
            kwargs = {
                "image": image,
                "detach": detach,
                "remove": remove,
            }
            
            if command:
                kwargs["command"] = command
            if name:
                kwargs["name"] = name
            if environment:
                kwargs["environment"] = environment
            if ports:
                kwargs["ports"] = ports
            if volumes:
                kwargs["volumes"] = volumes
            
            container = self.client.containers.run(**kwargs)
            
            if detach:
                return {
                    "success": True,
                    "container_id": container.short_id,
                    "name": container.name,
                    "status": container.status,
                }
            else:
                # For non-detached, container is the output bytes
                return {
                    "success": True,
                    "output": container.decode("utf-8") if isinstance(container, bytes) else str(container),
                }
        except Exception as e:
            logger.error(f"Docker run_container error: {e}")
            return {"error": str(e)}
    
    def stop_container(self, container_id: str, timeout: int = 10) -> Dict[str, Any]:
        """Stop a running container.
        
        Args:
            container_id: Container ID or name
            timeout: Seconds to wait before killing
            
        Returns:
            Result
        """
        if not container_id:
            return {"error": "container_id is required"}
        
        try:
            container = self.client.containers.get(container_id)
            container.stop(timeout=timeout)
            return {"success": True, "container_id": container.short_id, "status": "stopped"}
        except Exception as e:
            logger.error(f"Docker stop_container error: {e}")
            return {"error": str(e)}
    
    def remove_container(self, container_id: str, force: bool = False) -> Dict[str, Any]:
        """Remove a container.
        
        Args:
            container_id: Container ID or name
            force: Force removal of running container
            
        Returns:
            Result
        """
        if not container_id:
            return {"error": "container_id is required"}
        
        try:
            container = self.client.containers.get(container_id)
            container.remove(force=force)
            return {"success": True, "container_id": container_id, "status": "removed"}
        except Exception as e:
            logger.error(f"Docker remove_container error: {e}")
            return {"error": str(e)}
    
    def exec_command(self, container_id: str, command: str) -> Dict[str, Any]:
        """Execute command in a running container.
        
        Args:
            container_id: Container ID or name
            command: Command to execute
            
        Returns:
            Command output
        """
        if not container_id:
            return {"error": "container_id is required"}
        if not command:
            return {"error": "command is required"}
        
        try:
            container = self.client.containers.get(container_id)
            exit_code, output = container.exec_run(command)
            
            return {
                "success": exit_code == 0,
                "exit_code": exit_code,
                "output": output.decode("utf-8") if output else "",
            }
        except Exception as e:
            logger.error(f"Docker exec_command error: {e}")
            return {"error": str(e)}
    
    def get_logs(self, container_id: str, tail: int = 100) -> Dict[str, Any]:
        """Get container logs.
        
        Args:
            container_id: Container ID or name
            tail: Number of lines from end
            
        Returns:
            Log output
        """
        if not container_id:
            return {"error": "container_id is required"}
        
        try:
            container = self.client.containers.get(container_id)
            logs = container.logs(tail=tail)
            
            return {
                "container_id": container.short_id,
                "logs": logs.decode("utf-8") if logs else "",
            }
        except Exception as e:
            logger.error(f"Docker get_logs error: {e}")
            return {"error": str(e)}
    
    def pull_image(self, image: str) -> Dict[str, Any]:
        """Pull a Docker image.
        
        Args:
            image: Image name/tag
            
        Returns:
            Result
        """
        if not image:
            return {"error": "image is required"}
        
        try:
            img = self.client.images.pull(image)
            return {
                "success": True,
                "image_id": img.short_id,
                "tags": img.tags,
            }
        except Exception as e:
            logger.error(f"Docker pull_image error: {e}")
            return {"error": str(e)}
    
    def get_info(self) -> Dict[str, Any]:
        """Get Docker system info.
        
        Returns:
            System info
        """
        try:
            info = self.client.info()
            return {
                "containers": info.get("Containers"),
                "containers_running": info.get("ContainersRunning"),
                "images": info.get("Images"),
                "docker_version": info.get("ServerVersion"),
                "os": info.get("OperatingSystem"),
                "architecture": info.get("Architecture"),
                "memory": f"{info.get('MemTotal', 0) / 1024 / 1024 / 1024:.1f} GB",
                "cpus": info.get("NCPU"),
            }
        except Exception as e:
            logger.error(f"Docker get_info error: {e}")
            return {"error": str(e)}


def list_docker_containers(all_containers: bool = False) -> List[Dict[str, Any]]:
    """List Docker containers."""
    return DockerTool().list_containers(all_containers=all_containers)


def run_docker_container(image: str, command: Optional[str] = None) -> Dict[str, Any]:
    """Run a Docker container."""
    return DockerTool().run_container(image=image, command=command)
