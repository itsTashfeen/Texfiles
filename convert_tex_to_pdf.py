import os
import subprocess

def convert_tex_to_pdf(tex_root, pdf_root):
    for dirpath, _, filenames in os.walk(tex_root):
        relative_dir = os.path.relpath(dirpath, tex_root)
        pdf_dir = os.path.join(pdf_root, relative_dir)

        if not os.path.exists(pdf_dir):
            os.makedirs(pdf_dir)
            print(f"Created directory: {pdf_dir}")

        for filename in filenames:
            if filename.endswith(".tex"):
                tex_filepath = os.path.join(dirpath, filename)
                pdf_filepath = os.path.join(pdf_dir, filename.replace(".tex", ".pdf"))
                print(f"Converting {tex_filepath} to {pdf_filepath}...")

                try:
                    subprocess.run(
                        ['pdflatex', '-interaction=nonstopmode', '-output-directory', pdf_dir, tex_filepath],
                        check=True,
                        capture_output=True,
                        text=True
                    )
                    print("Conversion successful.")
                except subprocess.CalledProcessError as e:
                    print(f"Error converting {tex_filepath}:")
                    print(e.stderr)
                except FileNotFoundError:
                    print("Error: 'pdflatex' command not found.")
                    print("Please ensure you have a LaTeX distribution (like MiKTeX or TeX Live) installed and in your system's PATH.")
                    return

if __name__ == "__main__":
    tex_directory = r"C:\Users\Computer\Documents\GitHub\MathTex\Courses\.tex"
    pdf_directory = r"C:\Users\Computer\Documents\GitHub\MathTex\Courses\.pdf"

    convert_tex_to_pdf(tex_directory, pdf_directory)
    print("\nBatch conversion process finished.")