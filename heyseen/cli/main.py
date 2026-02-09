"""
HeySeen CLI - PDF to LaTeX Converter

Command-line interface for HeySeen.
"""

import click
from pathlib import Path
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
import time
import logging
import sys

from heyseen.core.pdf_loader import load_pdf
from heyseen.core.layout_analyzer import LayoutAnalyzer
from heyseen.core.content_extractor import ContentExtractor
from heyseen.core.tex_builder import TeXBuilder

console = Console()


def setup_logging(verbose: bool, output_dir: Path = None):
    """Setup logging configuration."""
    # Create logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    
    # Silence noisy third-party loggers
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('huggingface_hub').setLevel(logging.WARNING)
    logging.getLogger('transformers').setLevel(logging.WARNING)
    
    # Console handler (only show INFO+ unless verbose)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG if verbose else logging.INFO)
    console_formatter = logging.Formatter('%(levelname)s: %(message)s')
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # File handler (always log DEBUG to file if output_dir exists)
    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(output_dir / 'conversion.log', mode='w', encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)


@click.group()
@click.version_option(version="0.1.0", prog_name="HeySeen")
def cli():
    """
    HeySeen - Offline PDF to LaTeX Converter
    
    Convert PDF documents to editable LaTeX source code with images.
    Optimized for Apple Silicon (M1/M2/M3).
    """
    pass


@cli.command()
@click.argument("tex_file", type=click.Path(exists=True, path_type=Path))
@click.option(
    "-o",
    "--output",
    type=click.Path(path_type=Path),
    help="Path to save corrected file (default: {filename}_corrected.tex)",
)
@click.option(
    "--llm-url",
    type=str,
    default="http://localhost:11434",
    help="URL of Ollama server",
)
@click.option(
    "--model",
    type=str,
    default="qwen2.5-coder:7b",
    help="Ollama model name",
)
def improve(tex_file: Path, output: Path, llm_url: str, model: str):
    """
    Post-process an existing LaTeX file using LLM to correct OCR errors.
    
    This command reads a generated LaTeX file, splits it into chunks, and
    uses a local LLM to fix text errors (spelling, grammar) while preserving LaTeX / Math.
    """
    from heyseen.core.latex_corrector import LatexCorrector
    
    console.print(f"[bold green]HeySeen Improvement Mode[/bold green]")
    console.print(f"Target: {tex_file}")
    console.print(f"LLM: {llm_url} ({model})")
    
    corrector = LatexCorrector(llm_url=llm_url, model=model)
    
    output_path = str(output) if output else None
    final_path = corrector.correct_file(str(tex_file), output_path)
    
    console.print(f"[bold blue]Success![/bold blue] Saved corrected file to: {final_path}")


@cli.command()
@click.argument("pdf_file", type=click.Path(exists=True, path_type=Path))
@click.option(
    "-o",
    "--output",
    type=click.Path(path_type=Path),
    default="output",
    help="Output directory for LaTeX files",
)
@click.option(
    "--dpi",
    type=int,
    default=300,
    help="DPI for PDF rendering (higher = better quality, slower)",
)
@click.option(
    "--device",
    type=click.Choice(["mps", "cpu"]),
    default="mps",
    help="Device for inference (mps for Apple Silicon GPU, cpu for CPU-only)",
)
@click.option(
    "--verbose/--quiet",
    default=True,
    help="Print detailed progress information",
)
@click.option(
    "--math-ocr/--no-math-ocr",
    default=True,
    help="Enable Texify for accurate math OCR (slower but better quality)",
)
@click.option(
    "--pages",
    type=str,
    default=None,
    help="Page range to convert (e.g. '1-3', '5'). Default: all pages.",
)
@click.option(
    "--llm-url",
    type=str,
    default=None,
    help="URL of Ollama LLM for post-processing text (e.g., http://192.168.1.100:11434)",
)
def convert(pdf_file: Path, output: Path, dpi: int, device: str, verbose: bool, math_ocr: bool, pages: str, llm_url: str):
    """
    Convert a PDF file to LaTeX source code.
    
    Example:
        heyseen convert paper.pdf -o output/paper_tex --dpi 300
    """
    # Setup logging (both console and file)
    setup_logging(verbose, output_dir=output)
    
    console.print(f"\n[bold cyan]HeySeen PDF→LaTeX Converter[/bold cyan]")
    info_params = f"Device: {device.upper()} | Math OCR: {math_ocr}"
    if pages:
        info_params += f" | Pages: {pages}"
    if llm_url:
        info_params += f" | LLM: {llm_url} (DeepSeek-R1)"
    console.print(f"[dim]Version 0.1.0 | {info_params}[/dim]\n")
    
    logging.info(f"Starting conversion: {pdf_file} → {output}")
    logging.info(f"Settings: DPI={dpi}, Device={device}, MathOCR={math_ocr}, Pages={pages}, LLM={llm_url}")
    
    start_time = time.time()
    
    try:
        # Step 1: Load PDF
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("[cyan]Loading PDF...", total=None)
            pages_list = load_pdf(pdf_file, dpi=dpi, pages=pages)
            progress.update(task, completed=True)
        
        console.print(f"  ✓ Loaded [green]{len(pages_list)}[/green] page(s)\n")
        
        # Step 2: Detect layout
        console.print("[cyan]Detecting layout...[/cyan]")
        analyzer = LayoutAnalyzer(device=device, verbose=verbose, pdf_path=str(pdf_file))
        
        all_blocks = []
        total_blocks = 0
        for i, page in enumerate(pages_list, 1):
            blocks = analyzer.detect_layout(page.image)
            # Make sure to sort blocks in reading order (important for 2-column layouts)
            blocks = analyzer.sort_reading_order(blocks)
            all_blocks.append(blocks)
            total_blocks += len(blocks)
            if verbose:
                console.print(f"  Page {i}: {len(blocks)} blocks")
        
        console.print(f"  ✓ Detected [green]{total_blocks}[/green] blocks\n")
        
        # Step 3: Extract content
        console.print("[cyan]Extracting content (OCR)...[/cyan]")
        if math_ocr and verbose:
            console.print("  [dim]Loading Texify for math OCR...[/dim]")
        
        extractor = ContentExtractor(
            device=device,
            use_math_ocr=math_ocr,
            verbose=verbose,
            llm_url=llm_url
        )
        
        all_contents = []
        total_text = 0
        total_math = 0
        total_images = 0
        
        for i, (page, blocks) in enumerate(zip(pages_list, all_blocks), 1):
            contents = extractor.extract_page(
                page.image,
                blocks,
                output_dir=output / "images"
            )
            all_contents.append(contents)
            
            text_count = sum(1 for c in contents if c.text)
            math_count = sum(1 for c in contents if c.latex)
            image_count = sum(1 for c in contents if c.image_path)
            total_text += text_count
            total_math += math_count
            total_images += image_count
            
            if verbose:
                console.print(f"  Page {i}: {text_count} text, {math_count} math, {image_count} images")
        
        summary = f"  ✓ Extracted [green]{total_text}[/green] text"
        if total_math > 0:
            summary += f", [green]{total_math}[/green] math"
        if total_images > 0:
            summary += f", [green]{total_images}[/green] images"
        console.print(summary + "\n")
        
        # Step 4: Build LaTeX
        console.print("[cyan]Building LaTeX document...[/cyan]")
        builder = TeXBuilder(output_dir=output, verbose=False)
        
        document_info = {
            "title": pdf_file.stem.replace("_", " ").title(),
            "author": "HeySeen Converter",
        }
        
        main_tex_path = builder.build_document(
            contents_per_page=all_contents,
            blocks_per_page=all_blocks,
            document_info=document_info,
        )
        
        console.print(f"  ✓ Created [green]{main_tex_path}[/green]\n")
        
        # Summary
        elapsed = time.time() - start_time
        console.print("[bold green]✓ Conversion complete![/bold green]")
        console.print(f"\nOutput directory: [cyan]{output.absolute()}[/cyan]")
        console.print(f"Processing time: [yellow]{elapsed:.1f}s[/yellow]")
        console.print(f"Pages: [green]{len(pages_list)}[/green] | Blocks: [green]{total_blocks}[/green]\n")
        
        console.print("[dim]To compile the LaTeX document:[/dim]")
        console.print(f"[dim]  cd {output}[/dim]")
        console.print(f"[dim]  pdflatex main.tex[/dim]\n")
        
    except FileNotFoundError as e:
        logging.error(f"File not found: {e}")
        console.print(f"\n[bold red]Error:[/bold red] File not found: {e}\n", style="red")
        console.print("[dim]Check that the PDF file exists and path is correct.[/dim]\n")
        raise click.Abort()
    
    except PermissionError as e:
        logging.error(f"Permission denied: {e}")
        console.print(f"\n[bold red]Error:[/bold red] Permission denied: {e}\n", style="red")
        console.print("[dim]Check file/folder permissions or try a different output directory.[/dim]\n")
        raise click.Abort()
    
    except MemoryError:
        logging.error("Out of memory")
        console.print(f"\n[bold red]Error:[/bold red] Out of memory\n", style="red")
        console.print("[dim]Try:[/dim]")
        console.print("[dim]  - Lower DPI (e.g., --dpi 100)[/dim]")
        console.print("[dim]  - Disable math OCR (--no-math-ocr)[/dim]")
        console.print("[dim]  - Use CPU instead (--device cpu)[/dim]\n")
        raise click.Abort()
    
    except KeyboardInterrupt:
        logging.info("Conversion cancelled by user")
        console.print(f"\n[yellow]Conversion cancelled by user[/yellow]\n")
        raise click.Abort()
    
    except Exception as e:
        logging.exception(f"Unexpected error: {e}")
        console.print(f"\n[bold red]Unexpected Error:[/bold red] {e}\n", style="red")
        console.print(f"[dim]Check {output}/conversion.log for details.[/dim]\n")
        raise click.Abort()


@cli.command()
def info():
    """Show system information and dependencies"""
    console.print("\n[bold cyan]HeySeen System Information[/bold cyan]\n")
    
    import sys
    import platform
    
    console.print(f"Python: {sys.version.split()[0]}")
    console.print(f"Platform: {platform.system()} {platform.machine()}")
    
    try:
        import torch
        console.print(f"PyTorch: {torch.__version__}")
        console.print(f"MPS Available: {torch.backends.mps.is_available()}")
    except ImportError:
        console.print("PyTorch: [red]Not installed[/red]")
    
    try:
        import surya
        console.print(f"Surya OCR: {surya.__version__}")
    except ImportError:
        console.print("Surya OCR: [red]Not installed[/red]")
    
    console.print()


if __name__ == "__main__":
    cli()
