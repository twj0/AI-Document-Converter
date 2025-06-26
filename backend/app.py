# backend/app.py (Final version with corrected validation logic)
import logging
from pathlib import Path
from uuid import uuid4
from flask import Flask, request, render_template, send_from_directory, url_for, jsonify
from werkzeug.utils import secure_filename
from dotenv import dotenv_values

# --- AI模型配置 ---
AVAILABLE_AI_MODELS = {
    "gemini": {
        "name": "Google Gemini",
        "models": ["gemini-1.5-flash-latest", "gemini-pro"]
    },
    "openai": {
        "name": "OpenAI",
        "models": ["gpt-4-turbo", "gpt-3.5-turbo"]
    }
}

TASK_TO_EXTENSIONS = {
    'ppt_to_pdf': ['.ppt', '.pptx'],
    'doc_to_markdown_ai': ['.doc', '.docx'],
    'pdf_to_markdown_ai': ['.pdf'],
    'doc_to_markdown_simple': ['.doc', '.docx'],
}

BACKEND_DIR = Path(__file__).parent.resolve()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [FLASK_APP] - %(levelname)s - %(message)s')
config = dotenv_values(BACKEND_DIR / ".env")
app = Flask(__name__)
app.secret_key = 'a_very_secret_key_for_flash_messages'
TEMP_DIR = BACKEND_DIR / "temp_files"
OUTPUT_DIR = BACKEND_DIR / "output_files"
TEMP_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)


@app.route('/', methods=['GET'])
def index():
    return render_template('index.html', ai_config=AVAILABLE_AI_MODELS)


@app.route('/upload', methods=['POST'])
def upload_and_process():
    if 'file' not in request.files:
        return jsonify({'status': 'error', 'message': 'No file part in the request.'}), 400
    
    file = request.files['file']
    task_type = request.form.get('task_type')
    
    if file.filename == '' or not task_type:
        return jsonify({'status': 'error', 'message': 'No file selected or task type specified.'}), 400

    original_filename = file.filename
    original_stem = Path(original_filename).stem
    original_ext = Path(original_filename).suffix.lower()

    # =================================================================
    # THE FINAL, FINAL FIX: Corrected validation logic for all task types
    # =================================================================
    # 1. First, try to get the allowed extensions using the task_type directly.
    allowed_extensions = TASK_TO_EXTENSIONS.get(task_type)
    
    # 2. If it's not found (e.g., for old task names from a cached UI), handle it.
    #    (This part is more for robustness, the main fix is the line above)
    if not allowed_extensions:
        # We can simply check against a unified key if tasks are grouped, e.g. all Word tasks
        if 'doc_to_markdown' in task_type:
            allowed_extensions = ['.doc', '.docx']
        # Add other potential fallbacks if necessary
    
    if not allowed_extensions or original_ext not in allowed_extensions:
        return jsonify({
            'status': 'error',
            'message': f"File type mismatch: Task '{task_type}' doesn't support '{original_ext}' files."
        }), 400
    # =================================================================

    safe_stem = secure_filename(original_stem) or "file"
    filename = f"{safe_stem}{original_ext}"
    
    req_id = str(uuid4())
    input_path = TEMP_DIR / req_id / filename
    output_path_base = OUTPUT_DIR / req_id
    input_path.parent.mkdir(parents=True, exist_ok=True)
    output_path_base.mkdir(parents=True, exist_ok=True)
    file.save(input_path)

    ai_key_from_user = request.form.get('ai_api_key')

    try:
        from services import file_processor as fp

        if task_type == 'ppt_to_pdf':
            output_file = output_path_base / f"{Path(filename).stem}.pdf"
            fp.convert_to_pdf_com(str(input_path), str(output_file))
            download_url = url_for('download_file', request_id=req_id, filename=output_file.name)
            return jsonify({'status': 'success', 'download_url': download_url})

        elif task_type == 'doc_to_markdown_simple':
            output_file = output_path_base / f"{Path(filename).stem}.md"
            fp.convert_word_to_markdown_simple(str(input_path), str(output_file))
            download_url = url_for('download_file', request_id=req_id, filename=output_file.name)
            return jsonify({'status': 'success', 'download_url': download_url})
        
        elif '_ai' in task_type:
            text = fp.extract_text_smart(str(input_path))
            if not text.strip():
                 return jsonify({'status': 'error', 'message': 'Could not extract any text from the document.'}), 400
            
            provider = request.form.get('ai_provider')
            model = request.form.get('ai_model')

            if not provider or not model:
                return jsonify({'status': 'error', 'message': 'AI Provider and Model must be selected.'}), 400

            api_key = ai_key_from_user if ai_key_from_user else config.get(f"{provider.upper()}_API_KEY")

            if not api_key or "YOUR_" in api_key:
                return jsonify({'status': 'error', 'message': f"API Key for '{provider}' is not configured or provided."}), 400
            
            from services import ai_service as ais
            ai_provider = ais.get_ai_provider(provider, model, api_key)
            result = ai_provider.generate_structured_markdown(text, "General", Path(filename).suffix)
            markdown_content = result.get("markdown_content", "")
            
            if not markdown_content:
                return jsonify({'status': 'error', 'message': 'AI processing resulted in empty content.'}), 400
            
            output_file = output_path_base / f"{Path(filename).stem}.md"
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(markdown_content)
            
            download_url = url_for('download_file', request_id=req_id, filename=output_file.name)
            return jsonify({'status': 'success', 'download_url': download_url})
        
        else:
            return jsonify({'status': 'error', 'message': f"Invalid task type '{task_type}'."}), 400

    except Exception as e:
        logging.error(f"Processing failed for {filename}: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': f"An error occurred: {repr(e)}"}), 500


@app.route('/downloads/<request_id>/<filename>')
def download_file(request_id, filename):
    directory = OUTPUT_DIR / request_id
    return send_from_directory(directory, filename, as_attachment=True)


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8000, debug=True)