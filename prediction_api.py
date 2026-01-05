from flask import Flask, request, jsonify
import pandas as pd
import base64
import pickle
import xgboost
import numpy as np

app = Flask(__name__)

def apply_model_and_predict(data_json_list, model_base64_string):
    try:
        decoded_model = base64.b64decode(model_base64_string)
        model = pickle.loads(decoded_model)
    except Exception as e:
        raise Exception(f"Failed to load model: {e}")

    # تبدیل داده‌ها
    historical_data = pd.DataFrame(data_json_list)
    
    # هماهنگ‌سازی نام ستون‌ها (بسیار مهم)
    # فرض می‌کنیم n8n داده را با کلیدهای datetime و actual_load می‌فرستد
    # اگر نام ستون‌ها متفاوت است، اینجا map کنید
    historical_data['datetime'] = pd.to_datetime(historical_data['datetime'], format='%Y-%m-%dT%H:%M:%S', errors='coerce')
    historical_data.dropna(subset=['datetime'], inplace=True)
    historical_data = historical_data.sort_values('datetime')

    last_datetime = historical_data['datetime'].max()
    
    # دریافت 24 ساعت آخر (دقیقاً 24 رکورد نیاز داریم)
    # این داده‌ها هم برای آمار استفاده می‌شوند و هم به عنوان فیچر برای آینده
    last_24h_start = last_datetime - pd.Timedelta(hours=23)
    last_24h_data = historical_data[historical_data['datetime'] >= last_24h_start].copy()
    
    if len(last_24h_data) < 24:
        return {"error": f"Not enough data. Need at least 24 hours history, got {len(last_24h_data)}"}

    # -----------------------------------------
    # ساخت داده‌های آینده
    # -----------------------------------------
    future_datetimes = pd.date_range(
        start=last_datetime + pd.Timedelta(hours=1),
        periods=24,
        freq='h'
    )

    future_data = pd.DataFrame({'datetime': future_datetimes})

    # 1. Time Features
    future_data['hour_of_day'] = future_data['datetime'].dt.hour
    future_data['day_of_week'] = future_data['datetime'].dt.dayofweek
    future_data['month'] = future_data['datetime'].dt.month

    # 2. Lag Feature Construction
    # برای پیش‌بینی ساعت 1 فردا، ورودی lag_24 برابر است با ساعت 1 امروز (که در last_24h_data موجود است)
    # ما مقادیر actual_load از 24 ساعت گذشته را برمیداریم و به عنوان lag_24 برای آینده استفاده می‌کنیم
    future_data['lag_24'] = last_24h_data['actual_load'].values

    # ترتیب فیچرها باید دقیقاً مثل زمان آموزش باشد
    FEATURES = ['hour_of_day', 'day_of_week', 'month', 'lag_24']
    X_future = future_data[FEATURES]

    # پیش‌بینی
    predictions = model.predict(X_future)
    future_data['predicted_load'] = predictions

    # -----------------------------------------
    # خروجی سازی (مشابه قبل)
    # -----------------------------------------
    past_24h_summary = []
    for _, row in last_24h_data.iterrows():
        past_24h_summary.append({
            'datetime': row['datetime'].strftime('%Y-%m-%dT%H:%M:%S'),
            'actual_load': float(row.get('actual_load', 0)),
            'type': 'actual'
        })

    future_24h_summary = []
    for _, row in future_data.iterrows():
        future_24h_summary.append({
            'datetime': row['datetime'].strftime('%Y-%m-%dT%H:%M:%S'),
            'predicted_load': float(row['predicted_load']),
            'type': 'predicted'
        })

    # آمارها
    past_loads = last_24h_data['actual_load']
    future_loads = future_data['predicted_load']

    statistics = {
        'past_24h': {
            'average': float(past_loads.mean()),
            'max': float(past_loads.max()),
            'min': float(past_loads.min())
        },
        'future_24h': {
            'average': float(future_loads.mean()),
            'max': float(future_loads.max()),
            'min': float(future_loads.min())
        }
    }

    return {
        'past_24h_data': past_24h_summary,
        'future_24h_data': future_24h_summary,
        'statistics': statistics
    }

@app.route('/predict', methods=['POST'])
def predict_load():
    try:
        data = request.get_json()
        model_b64 = data.get('model_data')
        new_data_list = data.get('new_data') # این باید شامل تاریخچه باشد
        
        if not model_b64 or not new_data_list:
            return jsonify({"error": "Missing data"}), 400
        
        result = apply_model_and_predict(new_data_list, model_b64)
        return jsonify(result), 200

    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002)