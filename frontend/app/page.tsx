'use client'

import { useState, useEffect } from 'react'
import axios from 'axios'

export default function Home() {
  const [file, setFile] = useState<File | null>(null)
  const [params, setParams] = useState({
    press_per_kg: 0,
    kouzan_per_kg: 0,
    transport_cost: 0,
  })
  const [loading, setLoading] = useState(false)

  // ページが読み込まれた時に、バックエンドから基本パラメータを取得する
  useEffect(() => {
    axios.get('http://localhost:8000/api/parameters')
      .then(res => {
        setParams(res.data)
      })
      .catch(err => {
        console.error("パラメータの取得に失敗:", err)
        alert("バックエンドとの接続に失敗しました。FastAPIサーバーが起動しているか確認してください。")
      })
  }, [])

  const handleParamChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target
    setParams(prev => ({ ...prev, [name]: Number(value) }))
  }

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!file) {
      alert('PDFファイルを選択してください。');
      return;
    }
    setLoading(true);

    const formData = new FormData();
    formData.append('file', file);
    formData.append('params_str', JSON.stringify(params));

    try {
      // ★★★ 正式なAPIである /api/analyze-sheet を呼び出す ★★★
      const res = await axios.post('http://localhost:8000/api/analyze-sheet', formData, {
        responseType: 'blob', // PDFを受け取るためにblobを指定
      });

      // --- PDFダウンロード処理 ---
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'valuation_report.pdf');
      document.body.appendChild(link);
      link.click();
      link.parentNode?.removeChild(link);

    } catch (err) {
      console.error("アップロードまたは解析に失敗:", err);
      alert("処理に失敗しました。バックエンドのターミナルでエラーを確認してください。");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="container mx-auto p-8">
      <h1 className="text-3xl font-bold mb-6">車両価値算定ツール</h1>
      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="p-6 border rounded-lg">
          <h2 className="text-xl font-semibold mb-3">① オークション出品票PDF</h2>
          <input type="file" accept="application/pdf" onChange={(e) => setFile(e.target.files?.[0] || null)} />
        </div>
        <div className="p-6 border rounded-lg">
          <h2 className="text-xl font-semibold mb-3">② 価値算定パラメータ</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label htmlFor="press_per_kg">プレス単価 (円/kg)</label>
              <input type="number" name="press_per_kg" value={params.press_per_kg} onChange={handleParamChange} className="mt-1 block w-full rounded-md border-gray-300 shadow-sm p-2" />
            </div>
            <div>
              <label htmlFor="kouzan_per_kg">甲山単価 (円/kg)</label>
              <input type="number" name="kouzan_per_kg" value={params.kouzan_per_kg} onChange={handleParamChange} className="mt-1 block w-full rounded-md border-gray-300 shadow-sm p-2" />
            </div>
            <div>
              <label htmlFor="transport_cost">輸送費 (円)</label>
              <input type="number" name="transport_cost" value={params.transport_cost} onChange={handleParamChange} className="mt-1 block w-full rounded-md border-gray-300 shadow-sm p-2" />
            </div>
          </div>
        </div>
        <button type="submit" disabled={!file || loading} className="w-full bg-blue-600 text-white font-bold py-3 px-4 rounded-lg hover:bg-blue-700 disabled:bg-gray-400">
          {loading ? '処理中...' : '価値を算定してレポート出力'}
        </button>
      </form>
    </main>
  )
}