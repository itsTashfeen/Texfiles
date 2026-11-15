import pymupdf
import os

def sanitize_filename(name):
    # Replace colons, slashes, and all other forbidden Windows characters with dashes
    for char in [':', '/', '\\', '<', '>', '|', '*', ';']:
        name = name.replace(char, ' - ')
    
    # Strip straight and curly quotes, question marks
    for char in ["'", '"', '?', '‘', '’', '“', '”']:
        name = name.replace(char, '')
        
    # Clean up any double spaces created by replacement
    return " ".join(name.split()).strip()

def split_pdf_by_bookmarks(pdf_path, output_dir, organize_folders, create_subfolders):
    # Open the document
    doc = pymupdf.open(pdf_path)
    raw_toc = doc.get_toc()  # Returns a list of [level, title, page_number]
    
    if not raw_toc:
        print("No bookmarks found in this PDF.")
        return

    # 1. FILTER THE TOC
    ignore_titles = ["exercises"]
    
    toc = []
    for item in raw_toc:
        level, title, page_num = item
        if title.strip().lower() not in ignore_titles:
            toc.append(item)

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    print(f"\nFound {len(toc)} valid sections. Processing...")

    # 2. IDENTIFY PARENT FOLDERS
    is_parent = [False] * len(toc)
    if organize_folders:
        for i in range(len(toc) - 1):
            if toc[i][0] == 1 and toc[i+1][0] > 1:
                is_parent[i] = True

    current_folder = None

    for i in range(len(toc)):
        level, title, start_page = toc[i]
        
        # PyMuPDF pages are 0-indexed, but TOC page numbers are 1-indexed
        start_idx = start_page - 1
        
        # Determine where this section ends
        if i + 1 < len(toc):
            # Stop EXACTLY ON the start page of the next section
            end_idx = toc[i+1][2] - 1 
            
            # Prevent negative slicing
            if end_idx < start_idx:
                end_idx = start_idx
        else:
            end_idx = doc.page_count - 1

        # 3. DIRECT FILES TO FOLDERS AND CREATE .TEX SCAFFOLDING
        if organize_folders:
            if level == 1:
                if is_parent[i]:
                    # Top bookmark with children -> set as active folder
                    current_folder = sanitize_filename(title)
                else:
                    # Top bookmark without children -> drop in root
                    current_folder = None 

            if current_folder:
                base_save_dir = os.path.join(output_dir, current_folder)
            else:
                base_save_dir = output_dir
        else:
            base_save_dir = output_dir

        clean_title = sanitize_filename(title)
        
        # If we are inside an organized chapter folder and subfolders are enabled
        if organize_folders and create_subfolders and current_folder:
            pdf_dir = os.path.join(base_save_dir, "Book PDF")
            hw_dir = os.path.join(base_save_dir, "Homework")
            ps_dir = os.path.join(base_save_dir, "Problem Sets")
            bs_dir = os.path.join(base_save_dir, "Book Section")
            
            # Create subdirectories if missing
            for d in [pdf_dir, hw_dir, ps_dir, bs_dir]:
                if not os.path.exists(d):
                    os.makedirs(d)
            
            out_pdf_path = os.path.join(pdf_dir, f"{clean_title}.pdf")
            
            # Create the empty .tex files
            tex_files = [
                (hw_dir, f"(Homework) {clean_title}.tex"),
                (ps_dir, f"(Problem Set) {clean_title}.tex"),
                (bs_dir, f"(Book Section) {clean_title}.tex")
            ]
            for tex_dir, tex_name in tex_files:
                tex_path = os.path.join(tex_dir, tex_name)
                if not os.path.exists(tex_path):
                    open(tex_path, 'w').close()  # Creates the empty file
        else:
            # Standard saving without the subfolder/.tex structure
            if not os.path.exists(base_save_dir):
                os.makedirs(base_save_dir)
            out_pdf_path = os.path.join(base_save_dir, f"{clean_title}.pdf")

        # 4. EXTRACT AND SAVE THE PDF
        new_doc = pymupdf.open()
        new_doc.insert_pdf(doc, from_page=start_idx, to_page=end_idx)
        new_doc.save(out_pdf_path)
        new_doc.close()
        
        if organize_folders and create_subfolders and current_folder:
            print(f"Processed: {clean_title} (PDF & .tex files generated)")
        else:
            print(f"Created PDF: {out_pdf_path}")

    doc.close()
    print("\nAll sections extracted and structured successfully!")

if __name__ == "__main__":
    print("--- Ultimate PDF Bookmark Splitter & Tex Generator ---")
    
    # 1. Get the FULL path to the PDF
    pdf_path = input("Enter the FULL path to the PDF file: ").strip()
    
    # 2. Get the output directory for the split files
    output_dir = input("Enter the directory where you want to save the splits: ").strip()
    
    # Remove quotes just in case you use "Copy as path" in Windows
    pdf_path = pdf_path.strip('"').strip("'")
    output_dir = output_dir.strip('"').strip("'")
    
    # 3. Ask for folder grouping permission
    org_choice = input("Group splits into folders based on top-level bookmarks? (y/n): ").strip().lower()
    organize_folders = (org_choice == 'y')
    
    create_subfolders = False
    if organize_folders:
        # 4. Ask for .tex subfolder structure permission
        sub_choice = input("Create Homework, Problem Sets, Book Section subfolders and generate .tex files? (y/n): ").strip().lower()
        create_subfolders = (sub_choice == 'y')

    # Verify the file actually exists before running
    if os.path.exists(pdf_path) and pdf_path.lower().endswith('.pdf'):
        split_pdf_by_bookmarks(pdf_path, output_dir, organize_folders, create_subfolders)
    else:
        print(f"\nError: Could not find a valid PDF file at '{pdf_path}'. Please check your path and try again.")