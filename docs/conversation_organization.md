# Conversation Organization System

This document explains how to use the conversation organization system in NexAgent. The system automatically creates a dedicated folder for each conversation or prompt, saves all related materials to that folder, and generates a final output document in PDF or Markdown format.

## Features

- **Automatic Folder Creation**: Each conversation gets its own dedicated folder
- **Material Storage**: All materials used during a conversation are saved to the conversation folder
- **Final Output Generation**: Automatically generates a summary document in PDF or Markdown format
- **Organized Structure**: Keeps all conversations and their materials neatly organized

## Getting Started

### Running the Server

To start the API server with conversation organization features, run:

```bash
python run_api_server_with_organization.py
```

This will start the server at http://127.0.0.1:8000 by default.

You can specify a different host and port using command-line arguments:

```bash
python run_api_server_with_organization.py --host 0.0.0.0 --port 8080
```

### Folder Structure

The system creates the following folder structure for each conversation:

```
data_store/
  conversations/
    {conversation_id}/
      metadata.json       # Conversation metadata
      messages.json       # Conversation messages
      materials/          # Folder for saved materials
        {material_1}      # Material files
        {material_2}
        ...
      {title}_summary.md  # Markdown summary
      {title}_summary.pdf # PDF summary (if PDF generation is successful)
```



## Dependencies

The conversation organization system requires the following dependencies:

- `markdown`: For converting Markdown to HTML
- `pdfkit`: For converting HTML to PDF
- `wkhtmltopdf`: External dependency required by pdfkit

Install the Python dependencies with:

```bash
pip install markdown pdfkit
```

For PDF generation, you also need to install wkhtmltopdf:

- **Windows**: Download and install from [wkhtmltopdf.org](https://wkhtmltopdf.org/downloads.html)
- **macOS**: `brew install wkhtmltopdf`
- **Linux**: `apt-get install wkhtmltopdf` or equivalent for your distribution

## Troubleshooting

### PDF Generation Issues

If PDF generation fails, the system will fall back to generating only a Markdown file. This can happen if:

1. wkhtmltopdf is not installed
2. The content is too complex for conversion
3. There are permission issues

Check the logs for specific error messages.

### Missing Dependencies

If you encounter errors about missing modules, make sure you've installed all required dependencies:

```bash
pip install markdown pdfkit
```

## Extending the System

The conversation organization system is designed to be extensible. You can modify the `ConversationManager` and `ConversationHandler` classes to add more features, such as:

- Additional output formats
- Custom templates for the output documents
- Integration with external storage systems
- Automatic backup of conversations