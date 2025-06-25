# backend/app.py (The Final, Corrected Download Path)
import logging
import shutil
from pathlib import Path
from uuid import uuid4
from flask import Flask, request, render_template, send_from_directory, flash, redirect, url_for
from werkzeug.utils import secure_filename
from dotenv import dotenv_values

# --- 1. 定义一个绝对的基础路径 ---
# 这可以确保无论我们从哪里运行脚本，路径都是正确的。
BASE_DIR = Path(__file__).parent.resolve()

# --- 配置 ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [FLASK_APP] - %(levelname)s - %(message)s')
config = dotenv_values(BASE_DIR / ".env")
app = Flask(__name__)
app.secret_key = 'a_very_secret_key_for_flash_messages'

# --- 2. 使用绝对路径来定义文件夹 ---
TEMP_DIR = BASE_DIR / "temp_files"
OUTPUT_DIR = BASE_DIR / "output_files"
TEMP_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# --- 主页面路由 ---
@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

# --- 文件上传和处理路由 ---
@app.route('/upload', methods=['POST'])
def upload_and_process():
    if 'file' not in request.files:
        flash('No file part')
        return redirect(request.url)
    
    file = request.files['file']
    task_type = request.form.get('task_type')

    if file.filename == '' or not task_type:
        flash('No selected file or task type')
        return redirect(request.url)

    if file:
        filename = secure_filename(file.filename)
        req_id = str(uuid4())
        
        input_path = TEMP_DIR / req_id / filename
        output_path_base = OUTPUT_DIR / req_id
        input_path.parent.mkdir(parents=True, exist_ok=True)
        output_path_base.mkdir(parents=True, exist_ok=True)
        file.save(input_path)

        try:
            # 导入 services
            from services import file_processor as fp
            from services import ai_service as ais

            if task_type == 'ppt_to_pdf':
                output_file = output_path_base / f"{Path(filename).stem}.pdf"
                fp.convert_to_pdf_com(str(input_path), str(output_file))
                return redirect(url_for('download_file', request_id=req_id, filename=output_file.name))
            
            elif task_type in ['doc_to_markdown', 'docx_to_markdown', 'pdf_to_markdown']:
                output_file = output_path_base / f"{Path(filename).stem}.md"
                provider = config.get("AI_PROVIDER", "gemini")
                api_key = config.get(f"{provider.upper()}_API_KEY")
                model = config.get(f"{provider.upper()}_MODEL_NAME")
                
                if not api_key or not model: raise ValueError("AI provider not configured in .env file.")

                text = fp.extract_text_smart(str(input_path))
                ai_provider = ais.get_ai_provider(provider, model, api_key)
                result = ai_provider.generate_structured_markdown(text, "General", Path(filename).suffix)
                
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(result.get("markdown_content", ""))
                
                return redirect(url_for('download_file', request_id=req_id, filename=output_file.name))
            
            else: raise ValueError("Invalid task type.")

        except Exception as e:
            logging.error(f"Processing failed for {filename}: {e}", exc_info=True)
            flash(f"An error occurred during conversion: {e}")
            return redirect(url_for('index'))

# --- 3. 修正文件下载路由 ---
@app.route('/downloads/<request_id>/<filename>')
def download_file(request_id, filename):
    """提供转换后文件的下载。"""
    # 使用绝对路径来查找目录，万无一失
    directory = OUTPUT_DIR / request_id
    logging.info(f"Attempting to download file from directory: {directory.resolve()}")
    if not directory.is_dir():
        logging.error(f"Download directory not found: {directory.resolve()}")
        return "Download directory not found.", 404
    
    return send_from_directory(directory, filename, as_attachment=True)

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8000, debug=True)