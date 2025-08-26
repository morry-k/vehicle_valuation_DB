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

def get_specs_from_llm(maker: str, car_name: str, model_code: str) -> dict:
    """
    生成AIを使用して車両のスペック情報を取得し、辞書形式で返す
    """
    prompt = f"""
あなたは日本の自動車スペックに関する専門家です。
以下の車両情報に基づいて、必要なスペックを調べて**JSON形式**で回答してください。

# 車両情報:
- メーカー: {maker}
- 車名: {car_name}
- 型式: {model_code}

# 取得したい情報:
- エンジン型式 (engine_model)
- 車両重量 (weight_kg)
- 触媒型式 (catalyst_model)

# 出力形式の例:
```json
{{
  "engine_model": "2ZR-FE",
  "weight_kg": 1240,
  "catalyst_model": null
}}
もし情報が見つからない、または特定できない場合は、該当する値を null としてください。
余計な説明は含めず、JSONオブジェクトのみを返してください。
"""

    try:
        response = model.generate_content(prompt)
        # レスポンスからJSON部分のみを抽出
        json_text = response.text.strip().replace("```json", "").replace("```", "")
        specs = json.loads(json_text)
        return specs
    except Exception as e:
        print(f"    - LLM APIエラー: {maker} {car_name} ({e})")
        return {
            "engine_model": None,
            "weight_kg": None,
            "catalyst_model": None
        }