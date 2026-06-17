import logging
import os
from datetime import datetime
from typing import Dict, Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from backend.app.core.config import settings

logger = logging.getLogger(__name__)

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "..", "templates")


class ReportService:
    def __init__(self):
        self.jinja_env = Environment(
            loader=FileSystemLoader(TEMPLATES_DIR),
            autoescape=select_autoescape(["html"]),
        )

    async def generate_pdf(self, location_data: Dict[str, Any], output_path: str) -> str:
        """
        Renders an HTML template and converts to PDF via WeasyPrint.
        Returns the path to the generated PDF.
        """
        try:
            from weasyprint import HTML
        except ImportError:
            raise RuntimeError("WeasyPrint is not installed")

        template = self.jinja_env.get_template("report.html")
        html_content = template.render(
            location=location_data,
            generated_at=datetime.now().strftime("%d.%m.%Y %H:%M"),
            company="Евроторг",
        )

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        HTML(string=html_content, base_url=TEMPLATES_DIR).write_pdf(output_path)
        logger.info("PDF report generated: %s", output_path)
        return output_path
