# app.py
import pandas as pd
from flask import Flask, render_template, jsonify, url_for # 导入 url_for
import os
from datetime import datetime
import traceback
import numpy as np # 用于处理可能的 NaN

# --- 配置 ---
DATA_FOLDER = 'data'
PREDICTION_FILENAME = 'final_recovered_predictions.csv'
TRUTH_FILENAME = 'final_recovered_truth.csv' # 需要真实值文件
GEO_INFO_FILENAME = 'station_geo_info.csv'
TIMESTAMP_COLUMN_INDEX = 0
NUM_OVERVIEW_STATIONS = 5 # 概览页显示的电站数量

# --- Flask 应用初始化 ---
app = Flask(__name__)

# --- 全局变量 ---
df_predictions = pd.DataFrame()
df_truth = pd.DataFrame() # 需要加载真实值
df_geo = pd.DataFrame()
STATION_NAMES = []
STATION_DISPLAY_INFO = [] # 用于二级页面下拉菜单
AVAILABLE_DATES = []

# --- 数据加载函数 (修改以加载真实值) ---
def load_data():
    global df_predictions, df_truth, df_geo, STATION_NAMES, STATION_DISPLAY_INFO, AVAILABLE_DATES
    # --- 加载预测数据 ---
    try:
        prediction_filepath = os.path.join(DATA_FOLDER, PREDICTION_FILENAME)
        df_predictions = pd.read_csv(prediction_filepath, index_col=TIMESTAMP_COLUMN_INDEX, parse_dates=True)
        STATION_NAMES = df_predictions.columns.tolist() # 以预测文件的列作为基准站点列表
        print(f"成功加载预测数据: {prediction_filepath}")
        if not df_predictions.empty:
            AVAILABLE_DATES = sorted(df_predictions.index.normalize().unique().strftime('%Y-%m-%d').tolist())
        else:
            AVAILABLE_DATES = []
    except FileNotFoundError:
        print(f"错误：无法找到预测文件 '{PREDICTION_FILENAME}'。")
        STATION_NAMES = []
        AVAILABLE_DATES = []
        df_predictions = pd.DataFrame() # 确保为空
    except Exception as e:
        print(f"加载预测数据时出错: {e}")
        traceback.print_exc()
        STATION_NAMES = []
        AVAILABLE_DATES = []
        df_predictions = pd.DataFrame()

    # --- 加载真实数据 ---
    try:
        truth_filepath = os.path.join(DATA_FOLDER, TRUTH_FILENAME)
        df_truth = pd.read_csv(truth_filepath, index_col=TIMESTAMP_COLUMN_INDEX, parse_dates=True)
        print(f"成功加载真实数据: {truth_filepath}")
        # 可选：确保真实数据的索引和列与预测数据对齐（如果需要严格比较）
        # if not df_predictions.empty and not df_truth.empty:
        #     common_index = df_predictions.index.intersection(df_truth.index)
        #     common_columns = df_predictions.columns.intersection(df_truth.columns)
        #     df_predictions = df_predictions.loc[common_index, common_columns]
        #     df_truth = df_truth.loc[common_index, common_columns]
        #     STATION_NAMES = df_predictions.columns.tolist() # 更新基准站点列表
        #     print("预测和真实数据已对齐。")
    except FileNotFoundError:
        print(f"警告：未找到真实数据文件 '{TRUTH_FILENAME}'。概览页实际值将不可用。")
        df_truth = pd.DataFrame() # 确保为空
    except Exception as e:
        print(f"加载真实数据时出错: {e}")
        traceback.print_exc()
        df_truth = pd.DataFrame()

    # --- 加载地理信息数据 (逻辑不变) ---
    try:
        geo_info_filepath = os.path.join(DATA_FOLDER, GEO_INFO_FILENAME)
        df_geo = pd.read_csv(geo_info_filepath)
        print(f"成功加载地理信息: {geo_info_filepath}")
        required_geo_cols = ['station_id', 'longitude', 'latitude']
        if not all(col in df_geo.columns for col in required_geo_cols):
            print(f"警告：地理信息文件缺少必要的列 ({required_geo_cols})。")
            df_geo = pd.DataFrame()
    except FileNotFoundError:
        print(f"警告：未找到地理信息文件 '{GEO_INFO_FILENAME}'。")
        df_geo = pd.DataFrame()
    except Exception as e:
        print(f"加载地理信息时出错: {e}")
        traceback.print_exc()
        df_geo = pd.DataFrame()

    # --- 准备二级页面站点显示信息列表 (逻辑不变) ---
    STATION_DISPLAY_INFO = []
    geo_map = pd.DataFrame()
    if not df_geo.empty:
        try:
            df_geo['station_id_str'] = df_geo['station_id'].astype(str)
            geo_map = df_geo.set_index('station_id_str')
        except Exception as e: print(f"准备地理信息映射出错: {e}")

    for index, station_name in enumerate(STATION_NAMES, start=1):
        display_text = f"光伏电站{index} (ID:{station_name}, 无地理信息)"
        if not geo_map.empty and station_name in geo_map.index:
            try:
                lon = geo_map.loc[station_name, 'longitude']
                lat = geo_map.loc[station_name, 'latitude']
                display_text = f"经:{lon:.2f}, 纬:{lat:.2f} (ID:光伏电站{index})"
            except Exception as e: display_text = f"光伏电站{index} (ID:{station_name}, 地理信息错误)"
        STATION_DISPLAY_INFO.append({'id': station_name, 'display': display_text})
    print(f"二级页面站点显示信息准备完成。")


# --- 辅助函数：获取概览数据 ---
def get_overview_data():
    overview_data = []
    if df_predictions.empty or df_truth.empty:
        print("警告：预测或真实数据为空，无法生成概览数据。")
        # 可以返回一些默认结构或提示信息
        for i, station_id in enumerate(STATION_NAMES[:NUM_OVERVIEW_STATIONS], start=1):
             overview_data.append({
                'id': station_id,
                'name': f"光伏电站 {i}",
                'actual': 'N/A',
                'predicted': 'N/A',
                'color': 'grey' # 灰色表示数据不可用
            })
        return overview_data

    try:
        now = datetime.now()
        current_hm = now.strftime('%H:%M')
        print(f"当前时间 (HH:MM): {current_hm}")

        # 查找最新的 <= current_hm 的时间点
        valid_times_pred = df_predictions[df_predictions.index.strftime('%H:%M') <= current_hm].index
        valid_times_truth = df_truth[df_truth.index.strftime('%H:%M') <= current_hm].index

        latest_time = pd.NaT # 初始化为 Not a Time

        # 需要两个DataFrame都有有效时间才行
        if not valid_times_pred.empty and not valid_times_truth.empty:
             latest_time_pred = valid_times_pred.max()
             latest_time_truth = valid_times_truth.max()
             # 取两者中较早的那个，以确保两者都有数据（或者根据业务逻辑决定）
             # 或者，更简单的是，假设它们时间戳基本一致，用预测的时间戳
             latest_time = latest_time_pred
             print(f"找到的最近匹配时间点: {latest_time}")
        else:
             print(f"警告：在 {current_hm} 或之前找不到同时有效的预测和真实数据时间点。")
             # 如果找不到，可以返回 N/A
             for i, station_id in enumerate(STATION_NAMES[:NUM_OVERVIEW_STATIONS], start=1):
                overview_data.append({'id': station_id, 'name': f"光伏电站 {i}", 'actual': 'N/A', 'predicted': 'N/A', 'color': 'grey'})
             return overview_data

        # 如果找到了有效时间点
        if pd.notna(latest_time):
            # 获取前 N 个电站的数据
            for i, station_id in enumerate(STATION_NAMES[:NUM_OVERVIEW_STATIONS], start=1):
                station_name = f"光伏电站 {i}"
                actual_value = np.nan
                predicted_value = np.nan
                color = 'grey' # 默认灰色

                # 尝试获取数据，处理可能的 KeyError 或时间点不存在的情况
                try:
                    if latest_time in df_truth.index and station_id in df_truth.columns:
                         actual_value = df_truth.loc[latest_time, station_id]
                    if latest_time in df_predictions.index and station_id in df_predictions.columns:
                         predicted_value = df_predictions.loc[latest_time, station_id]

                    # 计算颜色，仅当两个值都是有效数字时
                    if pd.notna(actual_value) and pd.notna(predicted_value):
                        diff = abs(actual_value - predicted_value)
                        if diff < 1:
                            color = 'green'
                        elif diff <= 2:
                            color = 'yellow'
                        else:
                            color = 'red'
                    else:
                        print(f"警告：站点 {station_id} 在 {latest_time} 缺少实际值或预测值。")

                except KeyError:
                    print(f"警告：站点 {station_id} 在数据列中不存在。")
                except Exception as e:
                    print(f"获取站点 {station_id} 数据时出错: {e}")
                    traceback.print_exc()

                overview_data.append({
                    'id': station_id, # 原始 ID 用于链接
                    'name': station_name,
                    # 格式化为字符串，处理 NaN
                    'actual': f"{actual_value:.2f}" if pd.notna(actual_value) else "N/A",
                    'predicted': f"{predicted_value:.2f}" if pd.notna(predicted_value) else "N/A",
                    'color': color
                })
        else: # 如果 latest_time 是 NaT
             print("未找到有效的最新时间点，返回 N/A 数据。")
             for i, station_id in enumerate(STATION_NAMES[:NUM_OVERVIEW_STATIONS], start=1):
                overview_data.append({'id': station_id, 'name': f"光伏电站 {i}", 'actual': 'N/A', 'predicted': 'N/A', 'color': 'grey'})

    except Exception as e:
        print(f"生成概览数据时发生严重错误: {e}")
        traceback.print_exc()
        # 出错时返回默认结构
        overview_data = []
        for i, station_id in enumerate(STATION_NAMES[:NUM_OVERVIEW_STATIONS], start=1):
             overview_data.append({'id': station_id, 'name': f"光伏电站 {i}", 'actual': '错误', 'predicted': '错误', 'color': 'grey'})

    return overview_data

# --- 路由定义 ---

# 一级页面：概览页
@app.route('/')
def landing_page():
    overview_data = get_overview_data()
    return render_template('landing.html', overview_data=overview_data)

# 二级页面：详情页 (使用 station_id 作为路径参数)
# 使用 name='details_page' 以便 url_for 引用
@app.route('/details/<path:station_id>', methods=['GET'], endpoint='details_page')
def details_page(station_id):
    print(f"--- [Flask Backend] Rendering details page for station_id: {station_id} ---")  # 添加这行
    # 验证 station_id 是否有效 (可选但推荐)
    if station_id not in STATION_NAMES:
        print(f"请求详情页错误：无效的站点 ID '{station_id}'")
        # 可以重定向到首页或显示错误页面
        return "无效的电站 ID", 404

    # 将所有必要信息传递给详情页模板
    # 注意：STATION_DISPLAY_INFO 包含所有站点的信息，用于下拉菜单
    return render_template('details.html',
                           station_info=STATION_DISPLAY_INFO,
                           dates=AVAILABLE_DATES,
                           selected_station_id=station_id) # 传递当前选中的ID

# API 路由 (保持不变，用于详情页图表数据)
@app.route('/api/data/<path:station_id>/<date_str>')
def get_daily_station_data(station_id, date_str):
    global df_predictions # 详情页API只提供预测数据

    if station_id not in STATION_NAMES:
        print(f"API 请求错误：无效的站点 ID '{station_id}'")
        return jsonify({"error": "无效的站点 ID"}), 404
    # ... (后续 API 逻辑与之前版本相同) ...
    try:
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        df_filtered = df_predictions.loc[df_predictions.index.date == target_date].copy()
        if df_filtered.empty or station_id not in df_filtered.columns:
             return jsonify({"station": station_id, "date": date_str, "timestamps": [], "predictions": [], "message": f"站点 '{station_id}' 在日期 '{date_str}' 没有预测数据"})
        prediction_data = df_filtered[station_id].tolist()
        timestamps = df_filtered.index.strftime('%H:%M:%S').tolist()
        return jsonify({"station": station_id, "date": date_str, "timestamps": timestamps, "predictions": prediction_data})
    except ValueError:
         return jsonify({"error": "无效的日期格式"}), 400
    except Exception as e:
        print(f"处理 API 请求 /api/data/{station_id}/{date_str} 时出错: {e}")
        traceback.print_exc()
        return jsonify({"error": "服务器内部错误"}), 500


# --- 运行应用 ---
if __name__ == '__main__':
    load_data()
    if not STATION_NAMES:
        print("\n警告：未能加载任何电站名称，请检查预测 CSV 文件。\n")
    app.run(debug=False, host='0.0.0.0', port=5000)
