"""Entry point para rodar o dashboard TUI."""
from dashboard.client import DashboardApp


def main():
    """Inicia o dashboard."""
    app = DashboardApp()
    app.run()


if __name__ == "__main__":
    main()
