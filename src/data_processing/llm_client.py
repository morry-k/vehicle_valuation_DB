import os
import json
import google.generativeai as genai
from dotenv import load_dotenv

# .envファイルから環境変数を読み込む
load_dotenv()

# APIキーを設定
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("APIキーが設定されていません。.envファイルを確認してください。")
genai.configure(api_key=api_key)

# モデルを設定
generation_config = {
  "temperature": 0.2,
  "top_p": 1,
  "top_k": 1,
  "max_output_tokens": 2048,
}
model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    generation_config=generation_config
)

# src/data_processing/llm_client.py

def get_specs_from_llm(model_code: str) -> dict: # 引数はmodel_codeのみ
    """
    生成AIを使用して車両のスペック情報を取得し、辞書形式で返す
    """
    prompt = f"""
あなたは日本の自動車の専門家です。
以下の車両型式に基づいて、メーカー、正式な車名、及び公開スペックを調べてJSON形式で回答してください。

# 車両情報:
- 型式: {model_code}

# 取得したい情報:
- メーカー (maker)
- 車名 (car_name)
- エンジン型式 (engine_model)
- 駆動方式 (drive_type)
- ボディタイプ (body_type)
- 車両総重量 (total_weight_kg)
- エンジン単体重量 (engine_weight_kg) # ← この行を追加
- グレード (grade) # ← この行を追加

# 出力形式の例:
```json
{{
  "maker": "トヨタ",
  "car_name": "プリウス",
  "engine_model": "2ZR-FXE",
  "drive_type": "HV",
  "body_type": "セダン",
  "total_weight_kg": 1350,
  "engine_weight_kg": 120, # ← この行を追加
  "grade": "S" # ← この行を追加
}}
もし情報が見つからない、または特定できない場合は、該当する値を null としてください。
余計な説明は含めず、JSONオブジェクトのみを返してください。
"""

    try:
        response = model.generate_content(prompt)
        json_text = response.text.strip().replace("```json", "").replace("```", "")
        specs = json.loads(json_text)
        return specs
    except Exception as e:
        print(f"    - LLM APIエラー: 型式={model_code} ({e})")
        return {} # エラー時は空の辞書を返す


# src/data_processing/llm_client.py

# ... (既存の get_specs_from_llm 関数はそのまま) ...

def get_full_engine_model_from_llm(maker: str, model_code: str, short_engine_model: str) -> str:
    """
    AIを使い、不完全なエンジン型式から正式名称を推定する
    """
    prompt = f"""
あなたは日本の自動車エンジンに関する専門家です。
以下の車両に搭載されているエンジンの、不完全な型式情報から、最も可能性の高い完全な正式名称を一つだけ回答してください。

# 車両情報
- メーカー: {maker or ""}
- 車両型式: {model_code or ""}
- 不完全なエンジン型式: {short_engine_model or ""}

# 回答形式の例
1ZZ-FE

余計な説明や記号は含めず、正式名称のみを返してください。
特定できない場合は "UNKNOWN" と回答してください。
"""
    try:
        response = model.generate_content(prompt)
        full_model_name = response.text.strip()
        if "UNKNOWN" in full_model_name:
            return str(short_engine_model) # 不明な場合は元の短い名前を返す
        return full_model_name
    except Exception:
        return str(short_engine_model) # エラー時も元の名前を返す