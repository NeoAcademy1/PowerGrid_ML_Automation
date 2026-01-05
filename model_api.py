from flask import Flask, request, jsonify
import pandas as pd
import xgboost as xgb
import pickle
import base64
from datetime import datetime

app = Flask(__name__)

@app.route('/train', methods=['POST'])
def train_model():
    try:
        data = request.json
        df = pd.DataFrame(data)
        
        # استاندارد کردن نام ستون زمان و بار
        # فرض بر این است که ورودی شما ستون‌هایی مثل 'datetime' و 'load' دارد
        # اگر نام‌ها متفاوت است اینجا تغییر نام دهید
        if 'actual_total_load_mw' in df.columns:
            df.rename(columns={'actual_total_load_mw': 'actual_load'}, inplace=True)
        if 'hour' in df.columns: # اگر ستون زمان hour نام دارد
             df.rename(columns={'hour': 'datetime'}, inplace=True)

        df['datetime'] = pd.to_datetime(df['datetime'])
        df = df.sort_values('datetime')

        # --- Feature Engineering ---
        
        # 1. Time Features
        df['hour_of_day'] = df['datetime'].dt.hour
        df['day_of_week'] = df['datetime'].dt.dayofweek
        df['month'] = df['datetime'].dt.month
        
        # 2. Lag Feature (مهمترین بخش)
        # مقدار بار در همین ساعت در روز قبل
        df['lag_24'] = df['actual_load'].shift(24)
        
        # حذف ردیف‌هایی که مقدار قبلی ندارند (24 ساعت اول)
        df = df.dropna()

        # Features & Target
        FEATURES = ['hour_of_day', 'day_of_week', 'month', 'lag_24']
        X = df[FEATURES]
        y = df['actual_load']
        
        # Train
        model = xgb.XGBRegressor(
            n_estimators=200, 
            max_depth=6, 
            learning_rate=0.05,
            objective='reg:squarederror'
        )
        model.fit(X, y)
        
        # Serialize
        model_bytes = pickle.dumps(model)
        model_base64 = base64.b64encode(model_bytes).decode('utf-8')
        
        return jsonify({
            'model': model_base64,
            'trained_at': datetime.now().isoformat(),
            'features': FEATURES,
            'status': 'success'
        })

    except Exception as e:
        return jsonify({'error': str(e), 'status': 'failed'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)