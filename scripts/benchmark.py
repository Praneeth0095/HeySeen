import time
import psutil
import os
import glob
from pathlib import Path
import statistics
from heyseen.core.layout_analyzer import LayoutAnalyzer
from heyseen.core.content_extractor import ContentExtractor
from heyseen.core.pdf_loader import load_pdf

def get_memory_usage():
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024  # MB

def benchmark_pipeline(pdf_paths, device="mps", math_ocr=True):
    print(f"🚀 Starting Benchmark | Device: {device} | MathOCR: {math_ocr}")
    print(f"Checking {len(pdf_paths)} files: {[p.name for p in pdf_paths]}")
    
    times = []
    memories = []
    page_counts = []
    
    # Initialize models once (cold start)
    print("Initializing models (Cold Start)...")
    start_init = time.time()
    analyzer = LayoutAnalyzer(device=device, verbose=False)
    # Enable verbose to debug extraction
    extractor = ContentExtractor(device=device, use_math_ocr=math_ocr, verbose=True)
    init_time = time.time() - start_init
    print(f"Model Init Time: {init_time:.2f}s")
    
    # Warmup
    print("Warming up...")
    # warm_pdf = pdf_paths[0]
    # pages = load_pdf(warm_pdf)
    # analyzer.detect_layout(pages[0])
    
    total_start = time.time()
    
    for pdf_path in pdf_paths:
        print(f"\nProcessing {pdf_path.name}...")
        file_start = time.time()
        start_mem = get_memory_usage()
        
        # 1. Load
        t0 = time.time()
        pages = load_pdf(pdf_path)
        load_time = time.time() - t0
        
        page_counts.append(len(pages))
        
        # 2. Layout & Extract (Page by Page)
        layout_times = []
        extract_times = []
        
        for page in pages:
            # Layout
            t1 = time.time()
            blocks = analyzer.detect_layout(page.image)
            layout_times.append(time.time() - t1)
            
            # Extract
            t2 = time.time()
            extractor.extract_page(page.image, blocks)
            extract_times.append(time.time() - t2)
            
        file_time = time.time() - file_start
        end_mem = get_memory_usage()
        
        print(f"  Time: {file_time:.2f}s ({file_time/len(pages):.2f}s/page)")
        print(f"  Mem:  {end_mem - start_mem:.1f} MB increased (Total: {end_mem:.1f} MB)")
        print(f"  Breakdown: Load={load_time:.2f}s, Layout={sum(layout_times):.2f}s, Extract={sum(extract_times):.2f}s")
        
        times.append(file_time)
        memories.append(end_mem)

    total_time = time.time() - total_start
    total_pages = sum(page_counts)
    
    print("\n" + "="*40)
    print("📊 BENCHMARK RESULTS")
    print("="*40)
    print(f"Total Pages:    {total_pages}")
    print(f"Total Time:     {total_time:.2f}s")
    print(f"Avg Speed:      {total_time/total_pages:.2f} s/page")
    print(f"Throughput:     {total_pages/total_time:.2f} pages/s")
    print(f"Peak Memory:    {max(memories):.1f} MB")
    print("="*40)

if __name__ == "__main__":
    # Use all test PDFs
    pdf_dir = Path("pdf_examples")
    pdfs = list(pdf_dir.glob("*.pdf"))
    
    benchmark_pipeline(pdfs, device="mps", math_ocr=True)
