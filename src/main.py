#!/usr/bin/env python3
"""
AIGateway-Zero: Lightweight AI Model Unified Gateway
轻量级AI模型统一网关

Entry point for the gateway server.
"""

import sys
import os
import argparse
import signal

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config
from gateway import AIGateway
from server import Server


def create_demo_config(path: str):
    """Create a demo configuration file."""
    config_content = """# AIGateway-Zero Configuration
# 轻量级AI模型统一网关配置

server:
  host: 0.0.0.0
  port: 8080
  workers: 4
  timeout: 60

gateway:
  default_model: gpt-4o
  fallback_enabled: true
  retry_attempts: 3
  retry_delay: 1.0
  load_balance_strategy: adaptive
  health_check_interval: 30
  rate_limit_enabled: true
  rate_limit_requests: 100
  rate_limit_window: 60

# Configure your LLM providers below
# 在下面配置你的LLM提供商

providers:
  openai:
    api_base: https://api.openai.com/v1
    api_key: ${OPENAI_API_KEY}
    models:
      - gpt-4o
      - gpt-4o-mini
      - gpt-4-turbo
    request_format: openai
    weight: 5
    timeout: 60

  anthropic:
    api_base: https://api.anthropic.com
    api_key: ${ANTHROPIC_API_KEY}
    models:
      - claude-3-5-sonnet-20241022
      - claude-3-opus-20240229
      - claude-3-haiku-20240307
    request_format: anthropic
    weight: 5
    timeout: 60

  gemini:
    api_base: https://generativelanguage.googleapis.com
    api_key: ${GEMINI_API_KEY}
    models:
      - gemini-1.5-pro
      - gemini-1.5-flash
    request_format: google
    weight: 3
    timeout: 60

  # Example: Local Ollama instance
  # 示例：本地Ollama实例
  ollama:
    api_base: http://localhost:11434/v1
    api_key: ollama
    models:
      - llama3.1
      - qwen2.5
      - mistral
    request_format: openai
    weight: 2
    timeout: 120

guardrails:
  enabled: false
  max_input_length: 32000
  max_output_length: 16000
  blocked_keywords: []
  allowed_models: []

logging:
  level: INFO
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

metrics:
  enabled: true
  retention_seconds: 86400
"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(config_content)
    print(f"Demo config created: {path}")


def main():
    parser = argparse.ArgumentParser(
        description="AIGateway-Zero: Lightweight AI Model Unified Gateway",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          # Start with default config (aigateway.yaml)
  %(prog)s -c config.yaml           # Start with custom config
  %(prog)s --init-config            # Create demo config file
  %(prog)s -p 9090                  # Start on port 9090

Environment Variables:
  AIGATEWAY_HOST              Server host (default: 0.0.0.0)
  AIGATEWAY_PORT              Server port (default: 8080)
  AIGATEWAY_DEFAULT_MODEL     Default model (default: gpt-4o)
  AIGATEWAY_LOAD_BALANCE      Load balance strategy (default: adaptive)
  AIGATEWAY_LOG_LEVEL         Log level (default: INFO)
  AIGATEWAY_PROVIDER_*        Provider configuration via env vars
        """
    )
    parser.add_argument(
        "-c", "--config",
        default="aigateway.yaml",
        help="Path to configuration file (default: aigateway.yaml)"
    )
    parser.add_argument(
        "-p", "--port",
        type=int,
        help="Override server port"
    )
    parser.add_argument(
        "-H", "--host",
        help="Override server host"
    )
    parser.add_argument(
        "--init-config",
        action="store_true",
        help="Create a demo configuration file and exit"
    )
    parser.add_argument(
        "--version",
        action="version",
        version="AIGateway-Zero v1.0.0"
    )

    args = parser.parse_args()

    if args.init_config:
        create_demo_config(args.config)
        return 0

    # Load configuration
    if os.path.exists(args.config):
        config = Config(args.config)
    else:
        print(f"Config file not found: {args.config}")
        print("Using default configuration. Create one with: aigateway --init-config")
        config = Config()

    # Override with CLI args
    if args.host:
        config.set("server", "host", value=args.host)
    if args.port:
        config.set("server", "port", value=args.port)

    host = config.get("server", "host", default="0.0.0.0")
    port = config.get("server", "port", default=8080)

    # Create gateway
    gateway = AIGateway(config)
    router = gateway.get_router()

    # Create and start server
    server = Server(
        host=host,
        port=port,
        router=router,
        logger=gateway.logger,
    )

    # Handle shutdown gracefully
    def signal_handler(signum, frame):
        print("\nShutting down AIGateway-Zero...")
        gateway.shutdown()
        server.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Print startup banner
    print("""
    ╔═══════════════════════════════════════════════════════════════╗
    ║                                                               ║
    ║   🤖 AIGateway-Zero v1.0.0                                    ║
    ║   Lightweight AI Model Unified Gateway                        ║
    ║   轻量级AI模型统一网关                                          ║
    ║                                                               ║
    ║   Server: http://{}:{:<5}                              ║
    ║   Docs:   http://{}:{}/gateway/status                  ║
    ║                                                               ║
    ╚═══════════════════════════════════════════════════════════════╝
    """.format(host, port, host, port))

    gateway.logger.info(f"AIGateway-Zero starting on {host}:{port}")
    gateway.logger.info(f"Load balance strategy: {gateway.load_balancer.strategy.value}")
    gateway.logger.info(f"Providers: {len(gateway.providers)}")
    gateway.logger.info("Press Ctrl+C to stop")

    try:
        server.start(blocking=True)
    except KeyboardInterrupt:
        signal_handler(signal.SIGINT, None)

    return 0


if __name__ == "__main__":
    sys.exit(main())
