# app.py
import pandas as pd
from flask import Flask, render_template, jsonify, url_for
import os
from datetime import datetime, timedelta
import traceback
import numpy as np
import logging
import sys # 导入 sys 用于强制刷新

TIME_OFFSET_HOURS = 8 # <--- 定义时间偏移量（小时）
# --- 配置 ---
# 获取 app.py 文件所在的目录
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
# 构建 data 文件夹的绝对路径
DATA_FOLDER = os.path.join(BASE_DIR, 'data') # 使用绝对路径

PREDICTION_FILENAME = 'final_recovered_predictions.csv'
TRUTH_FILENAME = 'final_recovered_truth.csv' # 需要真实值文件
GEO_INFO_FILENAME = 'station_geo_info.csv'
TIMESTAMP_COLUMN_INDEX = 0 # 假设时间戳在第一列
NUM_OVERVIEW_STATIONS = 5 # 概览页显示的电站数量

# --- Flask 应用初始化 ---
app = Flask(__name__)

# --- 配置 Flask logger ---
app.logger.setLevel(logging.DEBUG) # 设置日志级别为 DEBUG
# 输出到 stderr，Gunicorn 通常更容易捕获 stderr
handler = logging.StreamHandler(sys.stderr)
# 加入进程 ID 帮助区分 worker 日志
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - [PID:%(process)d] - %(message)s')
handler.setFormatter(formatter)
# 移除可能存在的旧 handlers，确保配置生效
for h in app.logger.handlers:
     app.logger.removeHandler(h)
app.logger.addHandler(handler)
app.logger.info("Flask logger configured.")
# --- Logger 配置结束 ---


# --- 全局变量 (无占位符) ---
df_predictions = pd.DataFrame()
df_truth = pd.DataFrame()
df_geo = pd.DataFrame()
STATION_NAMES = []
STATION_DISPLAY_INFO = []
AVAILABLE_DATES = []


# --- 数据加载函数 (恢复 pd.read_csv, 保留详细日志) ---
def load_data():
    global df_predictions, df_truth, df_geo, STATION_NAMES, STATION_DISPLAY_INFO, AVAILABLE_DATES
    app.logger.info("--- [load_data RESTORED] Function Start ---")
    app.logger.debug(f"--- [load_data RESTORED] Calculated BASE_DIR: {BASE_DIR}")
    app.logger.debug(f"--- [load_data RESTORED] Calculated DATA_FOLDER: {DATA_FOLDER}")

    # --- 调试：列出 data 目录内容 ---
    app.logger.debug(f"--- [load_data RESTORED] Checking contents of DATA_FOLDER ({DATA_FOLDER})...")
    try:
        if os.path.exists(DATA_FOLDER) and os.path.isdir(DATA_FOLDER):
            data_files = os.listdir(DATA_FOLDER)
            app.logger.info(f"--- [load_data RESTORED] Files found in DATA_FOLDER: {data_files}")
        else:
            app.logger.error(f"--- [load_data RESTORED] DATA_FOLDER does not exist or is not a directory at path: {DATA_FOLDER}")
            # 尝试列出 BASE_DIR 内容帮助诊断
            try:
                 app.logger.debug(f"--- [load_data RESTORED] Checking contents of BASE_DIR ({BASE_DIR})...")
                 base_contents = os.listdir(BASE_DIR)
                 app.logger.info(f"--- [load_data RESTORED] BASE_DIR contents: {base_contents}")
            except Exception as list_err:
                 app.logger.error(f"--- [load_data RESTORED] Error listing BASE_DIR: {list_err}", exc_info=True)

    except Exception as e:
        app.logger.error(f"--- [load_data RESTORED] Error listing DATA_FOLDER: {e}", exc_info=True)
    handler.flush()
    sys.stderr.flush()

    # --- 加载预测数据 ---
    prediction_filepath = os.path.join(DATA_FOLDER, PREDICTION_FILENAME)
    app.logger.debug(f"--- [load_data RESTORED] [Pred] Attempting path: {prediction_filepath}")
    try:
        app.logger.debug(f"--- [load_data RESTORED] [Pred] Checking existence...")
        if not os.path.exists(prediction_filepath):
            app.logger.error(f"--- [load_data RESTORED] [Pred] ERROR: File does not exist at path.")
            raise FileNotFoundError(f"Prediction file not found at {prediction_filepath}")

        app.logger.debug(f"--- [load_data RESTORED] [Pred] File exists. Attempting pd.read_csv...")
        # === 恢复读取 ===
        df_predictions = pd.read_csv(prediction_filepath, index_col=TIMESTAMP_COLUMN_INDEX, parse_dates=True)
        # === 检查加载后是否为空 ===
        if df_predictions.empty:
            app.logger.warning(f"--- [load_data RESTORED] [Pred] WARNING: pd.read_csv resulted in an empty DataFrame.")
        else:
            app.logger.info(f"--- [load_data RESTORED] [Pred] pd.read_csv SUCCESS. Shape: {df_predictions.shape}")
            STATION_NAMES = df_predictions.columns.tolist() # 仅在成功加载后设置
            AVAILABLE_DATES = sorted(df_predictions.index.normalize().unique().strftime('%Y-%m-%d').tolist()) # 仅在成功加载后设置
            app.logger.info(f"--- [load_data RESTORED] [Pred] Station names loaded: {len(STATION_NAMES)} stations.")
            app.logger.info(f"--- [load_data RESTORED] [Pred] Available dates loaded: {len(AVAILABLE_DATES)} dates.")

    except FileNotFoundError as e:
        app.logger.error(f"--- [load_data RESTORED] [Pred] CAUGHT FileNotFoundError: {e}")
        # 确保全局变量为空列表
        STATION_NAMES = []
        AVAILABLE_DATES = []
        df_predictions = pd.DataFrame()
    except Exception as e:
        app.logger.error(f"--- [load_data RESTORED] [Pred] CAUGHT Exception during read_csv: {e}", exc_info=True)
        STATION_NAMES = []
        AVAILABLE_DATES = []
        df_predictions = pd.DataFrame()
    handler.flush()
    sys.stderr.flush()


    # --- 加载真实数据 ---
    truth_filepath = os.path.join(DATA_FOLDER, TRUTH_FILENAME)
    app.logger.debug(f"--- [load_data RESTORED] [Truth] Attempting path: {truth_filepath}")
    try:
        app.logger.debug(f"--- [load_data RESTORED] [Truth] Checking existence...")
        if not os.path.exists(truth_filepath):
            app.logger.error(f"--- [load_data RESTORED] [Truth] ERROR: File does not exist at path.")
            raise FileNotFoundError(f"Truth file not found at {truth_filepath}")

        app.logger.debug(f"--- [load_data RESTORED] [Truth] File exists. Attempting pd.read_csv...")
        # === 恢复读取 ===
        df_truth = pd.read_csv(truth_filepath, index_col=TIMESTAMP_COLUMN_INDEX, parse_dates=True)
        # === 检查加载后是否为空 ===
        if df_truth.empty:
             app.logger.warning(f"--- [load_data RESTORED] [Truth] WARNING: pd.read_csv resulted in an empty DataFrame.")
        else:
             app.logger.info(f"--- [load_data RESTORED] [Truth] pd.read_csv SUCCESS. Shape: {df_truth.shape}")

    except FileNotFoundError as e:
        app.logger.error(f"--- [load_data RESTORED] [Truth] CAUGHT FileNotFoundError: {e}")
        df_truth = pd.DataFrame() # 确保为空
    except Exception as e:
        app.logger.error(f"--- [load_data RESTORED] [Truth] CAUGHT Exception during read_csv: {e}", exc_info=True)
        df_truth = pd.DataFrame()
    handler.flush()
    sys.stderr.flush()


    # --- 加载地理信息 ---
    geo_info_filepath = os.path.join(DATA_FOLDER, GEO_INFO_FILENAME)
    app.logger.debug(f"--- [load_data RESTORED] [Geo] Attempting path: {geo_info_filepath}")
    try:
        if os.path.exists(geo_info_filepath):
             app.logger.debug(f"--- [load_data RESTORED] [Geo] File exists. Attempting pd.read_csv...")
             df_geo = pd.read_csv(geo_info_filepath)
             if df_geo.empty:
                  app.logger.warning(f"--- [load_data RESTORED] [Geo] WARNING: pd.read_csv resulted in an empty DataFrame.")
             else:
                  app.logger.info(f"--- [load_data RESTORED] [Geo] pd.read_csv SUCCESS. Shape: {df_geo.shape}")
                  # --- 在成功加载 df_geo 后才准备 geo_map ---
                  try:
                      # 检查必要的列
                      required_geo_cols = ['station_id', 'longitude', 'latitude']
                      if not all(col in df_geo.columns for col in required_geo_cols):
                          app.logger.warning(f"--- [load_data RESTORED] [Geo] Missing required columns in geo file: {required_geo_cols}")
                          df_geo = pd.DataFrame() # 置空 geo 数据，因为无法使用
                      else:
                          df_geo['station_id_str'] = df_geo['station_id'].astype(str)
                          geo_map = df_geo.set_index('station_id_str')
                          app.logger.debug("--- [load_data RESTORED] Geo info map created.")
                  except Exception as map_err:
                      app.logger.error(f"--- [load_data RESTORED] Error creating geo map: {map_err}", exc_info=True)
                      df_geo = pd.DataFrame() # 出错则置空
                      geo_map = pd.DataFrame() # 确保 map 也为空
        else:
             app.logger.warning(f"--- [load_data RESTORED] [Geo] WARNING: File does not exist.")
             df_geo = pd.DataFrame()
    except Exception as e:
        app.logger.error(f"--- [load_data RESTORED] [Geo] CAUGHT Exception: {e}", exc_info=True)
        df_geo = pd.DataFrame()
    handler.flush()
    sys.stderr.flush()


    # --- 准备二级页面站点显示信息列表 ---
    STATION_DISPLAY_INFO = [] # 先清空
    # 如果 df_predictions 加载失败, STATION_NAMES 会是空列表, 循环不会执行
    app.logger.debug(f"--- [load_data RESTORED] Preparing display info for {len(STATION_NAMES)} stations...")
    geo_map = pd.DataFrame() # 重新定义在循环外，确保作用域
    if not df_geo.empty and 'station_id_str' in df_geo.columns: # 确保 geo_map 可以创建
        try:
             geo_map = df_geo.set_index('station_id_str')
        except Exception as e:
             app.logger.error(f"--- [load_data RESTORED] Error setting index for geo_map again: {e}")

    for index, station_name in enumerate(STATION_NAMES, start=1):
        display_text = f"光伏电站{index} (ID:{station_name}, 无地理信息)" # 默认值
        if not geo_map.empty and station_name in geo_map.index:
            try:
                lon = geo_map.loc[station_name, 'longitude']
                lat = geo_map.loc[station_name, 'latitude']
                display_text = f"经:{lon:.2f}, 纬:{lat:.2f} (ID:光伏电站{index})"
            except KeyError: # 处理列名不存在的情况
                 app.logger.warning(f"--- [load_data RESTORED] Geo details KeyError for {station_name}. Columns: {list(geo_map.columns)}")
                 display_text = f"光伏电站{index} (ID:{station_name}, 地理信息列缺失)"
            except Exception as e:
                app.logger.warning(f"--- [load_data RESTORED] Error getting geo details for {station_name}: {e}")
                display_text = f"光伏电站{index} (ID:{station_name}, 地理信息错误)"

        STATION_DISPLAY_INFO.append({'id': station_name, 'display': display_text})
    app.logger.info(f"--- [load_data RESTORED] Station display info prepared: {len(STATION_DISPLAY_INFO)} items.")


    # --- 最终检查 ---
    app.logger.info(f"--- [load_data RESTORED] Final check: df_predictions empty? {df_predictions.empty}")
    app.logger.info(f"--- [load_data RESTORED] Final check: df_truth empty? {df_truth.empty}")
    app.logger.info("--- [load_data RESTORED] Function End ---")
    handler.flush() # 再次确保刷新
    sys.stderr.flush()


# --- 辅助函数：获取概览数据 ---
def get_overview_data():
    global df_predictions, df_truth, STATION_NAMES # 确保引用全局变量
    app.logger.info("--- [get_overview_data] Function Start ---")
    overview_data = []

    # 再次检查全局 DataFrame 是否为空
    if df_predictions.empty or df_truth.empty:
        app.logger.warning("--- [get_overview_data] WARNING: df_predictions or df_truth is empty. Cannot generate overview.")
        # 返回带有占位符名称的默认结构
        overview_stations = STATION_NAMES[:NUM_OVERVIEW_STATIONS] if STATION_NAMES else [f'Placeholder_{i+1}' for i in range(NUM_OVERVIEW_STATIONS)]
        for i, station_id in enumerate(overview_stations, start=1):
            overview_data.append({
                'id': station_id,
                'name': f"光伏电站 {i}", # 使用序号名称
                'actual': 'N/A',
                'predicted': 'N/A',
                'color': 'grey'
            })
        return overview_data

    try:
        # --- 获取服务器当前时间并加上偏移量 ---
        now_server = datetime.now() # 获取服务器当前时间 (可能是 UTC)
        time_difference = timedelta(hours=TIME_OFFSET_HOURS) # 创建 6 小时的时间差
        now_local_estimated = now_server + time_difference # 计算估算的本地时间

        app.logger.info(f"--- [get_overview_data] Server time: {now_server.strftime('%Y-%m-%d %H:%M:%S')}")
        app.logger.info(f"--- [get_overview_data] Applying +{TIME_OFFSET_HOURS} hours offset.")
        app.logger.info(f"--- [get_overview_data] Estimated Local time: {now_local_estimated.strftime('%Y-%m-%d %H:%M:%S')}")
        # --- 使用估算的本地时间进行后续操作 ---

        current_hm = now_local_estimated.strftime('%H:%M')
        current_date = now_local_estimated.date()
        app.logger.info(f"--- [get_overview_data] Using Date for filtering: {current_date}, Using Time (HH:MM) for filtering: {current_hm}")
        # --- 时间修正结束 ---

        # 查找最新的 <= current_hm 的时间点
        # 确保索引是 DatetimeIndex
        if not isinstance(df_predictions.index, pd.DatetimeIndex) or not isinstance(df_truth.index, pd.DatetimeIndex):
             app.logger.error("--- [get_overview_data] ERROR: Predictions or Truth index is not DatetimeIndex!")
             raise TypeError("DataFrame index must be DatetimeIndex for time comparison")

        valid_times_pred_mask = df_predictions.index.strftime('%H:%M') <= current_hm
        valid_times_truth_mask = df_truth.index.strftime('%H:%M') <= current_hm

        valid_times_pred = df_predictions.index[valid_times_pred_mask]
        valid_times_truth = df_truth.index[valid_times_truth_mask]

        latest_time = pd.NaT

        if not valid_times_pred.empty and not valid_times_truth.empty:
             latest_time_pred = valid_times_pred.max()
             latest_time_truth = valid_times_truth.max()
             # 使用预测时间作为基准（假设两者时间戳对齐）
             latest_time = latest_time_pred
             # 检查真实数据在该时间点也存在
             if latest_time not in df_truth.index:
                 app.logger.warning(f"--- [get_overview_data] WARNING: Latest prediction time {latest_time} not found in truth data index. Trying truth max time.")
                 latest_time = latest_time_truth # 尝试用真实数据的最大时间
                 if latest_time not in df_predictions.index:
                      app.logger.error(f"--- [get_overview_data] ERROR: Latest truth time {latest_time} also not in prediction index. Cannot find common time.")
                      latest_time = pd.NaT # 回退到 NaT

             if pd.notna(latest_time):
                  app.logger.info(f"--- [get_overview_data] Found latest matching time point: {latest_time}")

        else:
             app.logger.warning(f"--- [get_overview_data] WARNING: No valid time points <= {current_hm} found in predictions or truth data.")

        # 根据 latest_time 获取数据
        if pd.notna(latest_time):
            target_stations = STATION_NAMES[:NUM_OVERVIEW_STATIONS] # 获取前 N 个站名
            app.logger.debug(f"--- [get_overview_data] Getting data for stations: {target_stations} at time {latest_time}")

            # 尝试一次性获取所需行的所有列，可能更高效
            try:
                actual_row = df_truth.loc[[latest_time], target_stations].iloc[0]
            except KeyError:
                app.logger.warning(f"--- [get_overview_data] KeyError getting actual row for time {latest_time} and stations {target_stations}.")
                actual_row = pd.Series(index=target_stations, dtype=float) # 返回空 Series
            except IndexError: # 如果 loc 结果为空
                 app.logger.warning(f"--- [get_overview_data] IndexError getting actual row for time {latest_time}.")
                 actual_row = pd.Series(index=target_stations, dtype=float)

            try:
                predicted_row = df_predictions.loc[[latest_time], target_stations].iloc[0]
            except KeyError:
                app.logger.warning(f"--- [get_overview_data] KeyError getting predicted row for time {latest_time} and stations {target_stations}.")
                predicted_row = pd.Series(index=target_stations, dtype=float)
            except IndexError:
                 app.logger.warning(f"--- [get_overview_data] IndexError getting predicted row for time {latest_time}.")
                 predicted_row = pd.Series(index=target_stations, dtype=float)


            for i, station_id in enumerate(target_stations, start=1):
                station_name = f"光伏电站 {i}"
                actual_value = actual_row.get(station_id, np.nan) # 使用 .get 防止 KeyError
                predicted_value = predicted_row.get(station_id, np.nan)
                color = 'grey'

                if pd.notna(actual_value) and pd.notna(predicted_value):
                    diff = abs(actual_value - predicted_value)
                    if diff < 1: color = 'green'
                    elif diff <= 2: color = 'yellow'
                    else: color = 'red'
                else:
                     app.logger.debug(f"--- [get_overview_data] Station {station_id} has NaN value at {latest_time}. Actual: {actual_value}, Predicted: {predicted_value}")


                overview_data.append({
                    'id': station_id,
                    'name': station_name,
                    'actual': f"{actual_value:.2f}" if pd.notna(actual_value) else "N/A",
                    'predicted': f"{predicted_value:.2f}" if pd.notna(predicted_value) else "N/A",
                    'color': color
                })
        else: # 如果 latest_time 是 NaT
             app.logger.warning("--- [get_overview_data] No valid latest_time found. Returning N/A data.")
             overview_stations = STATION_NAMES[:NUM_OVERVIEW_STATIONS] if STATION_NAMES else [f'Placeholder_{i+1}' for i in range(NUM_OVERVIEW_STATIONS)]
             for i, station_id in enumerate(overview_stations, start=1):
                overview_data.append({'id': station_id, 'name': f"光伏电站 {i}", 'actual': 'N/A', 'predicted': 'N/A', 'color': 'grey'})

    except Exception as e:
        app.logger.error(f"--- [get_overview_data] Unexpected error: {e}", exc_info=True)
        # 出错时返回默认结构
        overview_data = []
        overview_stations = STATION_NAMES[:NUM_OVERVIEW_STATIONS] if STATION_NAMES else [f'Placeholder_{i+1}' for i in range(NUM_OVERVIEW_STATIONS)]
        for i, station_id in enumerate(overview_stations, start=1):
             overview_data.append({'id': station_id, 'name': f"光伏电站 {i}", 'actual': '错误', 'predicted': '错误', 'color': 'grey'})

    app.logger.info(f"--- [get_overview_data] Function End. Returning {len(overview_data)} items.")
    return overview_data


# --- 路由定义 ---

# 一级页面：概览页
@app.route('/')
def landing_page():
    app.logger.info("--- [Route /] Request received ---")
    overview_data = get_overview_data()
    app.logger.debug(f"--- [Route /] Data for template: {overview_data}")
    return render_template('landing.html', overview_data=overview_data)

# 二级页面：详情页
@app.route('/details/<path:station_id>', methods=['GET'], endpoint='details_page')
def details_page(station_id):
    app.logger.info(f"--- [Route /details/{station_id}] Request received ---")
    # 使用全局的 STATION_NAMES 进行验证
    if station_id not in STATION_NAMES:
        app.logger.error(f"--- [Route /details/{station_id}] Invalid station ID requested.")
        return "无效的电站 ID", 404

    # 使用全局的 STATION_DISPLAY_INFO 和 AVAILABLE_DATES
    app.logger.debug(f"--- [Route /details/{station_id}] Rendering details template.")
    return render_template('details.html',
                           station_info=STATION_DISPLAY_INFO, # 用于下拉菜单
                           dates=AVAILABLE_DATES,
                           selected_station_id=station_id)

# API 路由 (用于详情页图表数据)
@app.route('/api/data/<path:station_id>/<date_str>')
def get_daily_station_data(station_id, date_str):
    global df_predictions # API 只返回预测数据
    app.logger.info(f"--- [API /api/data/{station_id}/{date_str}] Request received ---")

    if station_id not in STATION_NAMES:
        app.logger.error(f"--- [API /api/data/{station_id}/{date_str}] Invalid station ID.")
        return jsonify({"error": "无效的站点 ID"}), 404

    # 确保 df_predictions 已加载
    if df_predictions.empty:
         app.logger.error(f"--- [API /api/data/{station_id}/{date_str}] df_predictions is empty.")
         return jsonify({"error": "预测数据不可用"}), 503 # Service Unavailable

    try:
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        app.logger.debug(f"--- [API /api/data/{station_id}/{date_str}] Target date: {target_date}")

        # 过滤数据
        if not isinstance(df_predictions.index, pd.DatetimeIndex):
            app.logger.error("--- [API /api/data] df_predictions index is not DatetimeIndex!")
            raise TypeError("Index not DatetimeIndex")

        df_filtered = df_predictions.loc[df_predictions.index.date == target_date].copy()
        app.logger.debug(f"--- [API /api/data/{station_id}/{date_str}] Filtered data shape: {df_filtered.shape}")

        if df_filtered.empty or station_id not in df_filtered.columns:
             app.logger.warning(f"--- [API /api/data/{station_id}/{date_str}] No data found after filtering or column missing.")
             return jsonify({"station": station_id, "date": date_str, "timestamps": [], "predictions": [], "message": f"站点 '{station_id}' 在日期 '{date_str}' 没有预测数据"})

        prediction_data = df_filtered[station_id].tolist()
        timestamps = df_filtered.index.strftime('%H:%M:%S').tolist()
        app.logger.info(f"--- [API /api/data/{station_id}/{date_str}] Data found. Returning {len(timestamps)} timestamps.")
        return jsonify({"station": station_id, "date": date_str, "timestamps": timestamps, "predictions": prediction_data})

    except ValueError:
         app.logger.error(f"--- [API /api/data/{station_id}/{date_str}] Invalid date format.")
         return jsonify({"error": "无效的日期格式"}), 400
    except Exception as e:
        app.logger.error(f"--- [API /api/data/{station_id}/{date_str}] Unexpected error: {e}", exc_info=True)
        return jsonify({"error": "服务器内部错误"}), 500


# --- 调用 load_data() 在模块级别 ---
app.logger.info("--- Calling load_data() at module level ---")
load_data() # 加载全局数据


# --- 运行应用 (仅在本地直接运行 python app.py 时使用) ---
if __name__ == '__main__':
    # load_data() # 不再需要在这里调用
    if not STATION_NAMES:
        app.logger.warning("\n[Startup Check] Warning: No station names loaded.\n")
    app.logger.info("--- Starting Flask development server (won't run on Render) ---")
    # 对于本地测试，可以开启 debug，但部署时 Gunicorn 不会执行这里
    app.run(debug=True, host='0.0.0.0', port=5000)
