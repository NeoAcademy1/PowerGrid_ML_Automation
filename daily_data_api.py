from flask import Flask, jsonify
import pandas as pd
import os # برای مدیریت مسیرها

app = Flask(__name__)

# --- مسیر فایل‌های شما (این مسیرها را اصلاح کنید) ---
GENERATION_DATA_PATH = "C:/Users/b_sad/Desktop/DT/Personal/Projects/n8n_model_report/hourly_generation.csv" 
LOAD_DATA_PATH = "C:/Users/b_sad/Desktop/DT/Personal/Projects/n8n_model_report/hourly_load.csv"

# ----------------------------------------------------

@app.route('/get-generation-data', methods=['GET'])
def get_generation_data():
    """Endpoint برای خواندن داده‌های تولید برق روزانه."""
    print(f"Reading generation data from: {GENERATION_DATA_PATH}")
    if not os.path.exists(GENERATION_DATA_PATH):
        return jsonify({"error": f"File not found: {GENERATION_DATA_PATH}"}), 404
    try:
        df = pd.read_csv(GENERATION_DATA_PATH)
        # تبدیل به لیست دیکشنری‌ها (فرمت مناسب برای n8n)
        data_json = df.to_dict(orient='records')
        return jsonify(data_json)
    except Exception as e:
        return jsonify({"error": f"Error reading generation file: {str(e)}"}), 500

@app.route('/get-load-data', methods=['GET'])
def get_load_data():
    """Endpoint برای خواندن داده‌های مصرف برق روزانه."""
    print(f"Reading load data from: {LOAD_DATA_PATH}")
    if not os.path.exists(LOAD_DATA_PATH):
        return jsonify({"error": f"File not found: {LOAD_DATA_PATH}"}), 404
    try:
        df = pd.read_csv(LOAD_DATA_PATH)
        # تبدیل به لیست دیکشنری‌ها (فرمت مناسب برای n8n)
        data_json = df.to_dict(orient='records')
        return jsonify(data_json)
    except Exception as e:
        return jsonify({"error": f"Error reading load file: {str(e)}"}), 500

if __name__ == '__main__':
    # این API باید در پس‌زمینه اجرا شود تا n8n بتواند به آن دسترسی داشته باشد
    print("Starting Daily Data API on port 5001...")
    app.run(host='0.0.0.0', port=5001)