from praisonai_tools import (
    FileReadTool,
    WebsiteSearchTool,
    PDFSearchTool,
    DirectorySearchTool
)

def main():
    # Example 1: Search a website for specific information
    website_tool = WebsiteSearchTool(website='https://www.python.org')
    website_results = website_tool._run(
        search_query="What is Python?"
    )
    print("Website Search Results:", website_results)

    # Example 2: Search through PDF documents
    pdf_tool = PDFSearchTool(pdf="a-practical-guide-to-building-agents.pdf")
    pdf_results = pdf_tool._run(
        query="machine learning"
    )
    print("PDF Search Results:", pdf_results)

    # Example 3: Read a specific file
    file_tool = FileReadTool(file_path="test.txt")
    file_content = file_tool._run()
    print("File Content:", file_content)


if __name__ == "__main__":
    main() 