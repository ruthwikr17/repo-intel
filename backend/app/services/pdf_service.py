import re
import uuid
from pathlib import Path
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
OUTPUT_DIR = Path("/tmp/repoinsight_pdfs")
OUTPUT_DIR.mkdir(exist_ok=True)


def markdown_to_html(text: str) -> str:
    """Convert basic markdown to HTML for PDF rendering."""
    if not text:
        return ''
    
    lines = text.split('\n')
    html_lines = []
    in_code_block = False
    
    for line in lines:
        stripped = line.strip()
        
        # Code blocks
        if stripped.startswith('```'):
            if in_code_block:
                html_lines.append('</pre>')
                in_code_block = False
            else:
                html_lines.append('<pre>')
                in_code_block = True
            continue
        
        if in_code_block:
            html_lines.append(line.replace('<', '&lt;').replace('>', '&gt;'))
            continue
        
        # Headings
        if stripped.startswith('## '):
            html_lines.append(f'<h3>{stripped[3:]}</h3>')
        elif stripped.startswith('# '):
            html_lines.append(f'<h2>{stripped[2:]}</h2>')
        # Bullet points
        elif stripped.startswith('- ') or stripped.startswith('* '):
            content = stripped[2:]
            content = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', content)
            html_lines.append(f'<li>{content}</li>')
        # Bold inline
        elif stripped:
            content = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', stripped)
            content = re.sub(r'`(.*?)`', r'<code>\1</code>', content)
            html_lines.append(f'<p>{content}</p>')
        else:
            html_lines.append('<br>')
    
    return '\n'.join(html_lines)


def get_jinja_env() -> Environment:
    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))
    env.filters['md'] = markdown_to_html  # Register filter
    return env



def generate_contributor_guide(
    analysis: dict,
    repo: dict,
    opportunities: list,
) -> str:
    """
    Generate Contributor Guide PDF.
    Returns file path of generated PDF.
    """
    env = get_jinja_env()
    template = env.get_template("contributor_guide.html")

    html_content = template.render(
        repo=repo,
        analysis=analysis,
        opportunities=opportunities,
        generated_at=datetime.now().strftime("%B %d, %Y"),
        beginner_opps=[
            o for o in opportunities if o.get("difficulty_tier") == "beginner"
        ],
        intermediate_opps=[
            o for o in opportunities if o.get("difficulty_tier") == "intermediate"
        ],
        advanced_opps=[
            o for o in opportunities if o.get("difficulty_tier") == "advanced"
        ],
    )

    filename = f"contributor_guide_{uuid.uuid4().hex[:8]}.pdf"
    output_path = OUTPUT_DIR / filename
    pdf_bytes = HTML(string=html_content).write_pdf()
    with open(output_path, "wb") as f:
        f.write(pdf_bytes)
    return str(output_path)


def generate_executive_summary(
    analysis: dict,
    repo: dict,
) -> str:
    """Generate Executive Summary PDF. Returns file path."""
    env = get_jinja_env()
    template = env.get_template("executive_summary.html")

    html_content = template.render(
        repo=repo,
        analysis=analysis,
        generated_at=datetime.now().strftime("%B %d, %Y"),
    )

    filename = f"executive_summary_{uuid.uuid4().hex[:8]}.pdf"
    output_path = OUTPUT_DIR / filename
    pdf_bytes = HTML(string=html_content).write_pdf()
    with open(output_path, "wb") as f:
        f.write(pdf_bytes)
    return str(output_path)


def generate_code_quality_report(
    analysis: dict,
    repo: dict,
    opportunities: list,
) -> str:
    """Generate Code Quality Analysis PDF. Returns file path."""
    env = get_jinja_env()
    template = env.get_template("code_quality.html")

    # Extract metrics safely - handle case where it may be stored as JSON string
    raw_metrics = analysis.get("code_quality_metrics") or {}
    if isinstance(raw_metrics, str):
        import json
        try:
            raw_metrics = json.loads(raw_metrics)
        except Exception:
            raw_metrics = {}

    html_content = template.render(
        repo=repo,
        analysis=analysis,
        metrics=raw_metrics,
        opportunities=opportunities,
        generated_at=datetime.now().strftime("%B %d, %Y"),
    )

    filename = f"code_quality_{uuid.uuid4().hex[:8]}.pdf"
    output_path = OUTPUT_DIR / filename
    pdf_bytes = HTML(string=html_content).write_pdf()
    with open(output_path, "wb") as f:
        f.write(pdf_bytes)
    return str(output_path)


def generate_full_analysis(
    analysis: dict,
    repo: dict,
    opportunities: list,
) -> str:
    """
    Generate Full Analysis PDF combining all sections.
    This is the most comprehensive report.
    """
    env = get_jinja_env()
    template = env.get_template("full_analysis.html")

    html_content = template.render(
        repo=repo,
        analysis=analysis,
        opportunities=opportunities,
        generated_at=datetime.now().strftime("%B %d, %Y"),
        beginner_opps=[o for o in opportunities if o.get("difficulty_tier") == "beginner"],
        intermediate_opps=[o for o in opportunities if o.get("difficulty_tier") == "intermediate"],
        advanced_opps=[o for o in opportunities if o.get("difficulty_tier") == "advanced"],
    )

    filename = f"full_analysis_{uuid.uuid4().hex[:8]}.pdf"
    output_path = OUTPUT_DIR / filename
    HTML(string=html_content).write_pdf(str(output_path))
    return str(output_path)


