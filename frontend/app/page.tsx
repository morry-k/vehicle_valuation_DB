'use client'

import { useState, useEffect } from 'react'
import axios from 'axios'

export default function Home() {
  const [file, setFile] = useState<File | null>(null)
  const [params, setParams] = useState({
    engine_per_kg: 0,
    press_per_kg: 0,
    kouzan_per_kg: 0,
    harness_per_kg: 0,
    aluminum_wheels_price: 0,
    catalyst_price: 0,
    transport_cost: 0,
  })
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    axios.get(`${API_URL}/api/parameters`)
      .then(res => setParams(res.data))
      .catch(err => {
        console.error("パラメータの取得に失敗:", err)
        alert("バックエンドとの接続に失敗しました。")
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
      const res = await axios.post(`${API_URL}/api/analyze-sheet`, formData, {
        responseType: 'blob',
      });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement('a');
      link.href = url;
      const fileName = `valuation_report_${new Date().toISOString()}.pdf`;
      link.setAttribute('download', fileName);
      document.body.appendChild(link);
      link.click();
      
      setTimeout(() => {
        window.URL.revokeObjectURL(url);
        if (link.parentNode) {
            link.parentNode.removeChild(link);
        }
      }, 100);

    } catch (err) {
      console.error("アップロードまたは解析に失敗:", err);
      alert("処理に失敗しました。バックエンドのターミナルでエラーを確認してください。");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="flex min-h-screen w-full items-center justify-center bg-gray-100 p-4">
      <div className="w-full max-w-4xl rounded-2xl bg-white p-8 shadow-lg">
        <h1 className="mb-8 text-center text-3xl font-bold text-gray-800">
          車両価値算定ツール
        </h1>
        <form onSubmit={handleSubmit} className="space-y-8">
          <div className="rounded-lg border border-gray-200 p-6">
            <label htmlFor="file-upload" className="mb-3 block text-lg font-semibold text-gray-700">
              ① オークション出品票PDF
            </label>
            <input id="file-upload" type="file" accept="application/pdf" onChange={(e) => setFile(e.target.files?.[0] || null)} className="block w-full text-sm text-gray-500 file:mr-4 file:rounded-full file:border-0 file:bg-blue-50 file:px-4 file:py-2 file:font-semibold file:text-blue-700 hover:file:bg-blue-100" />
          </div>

          <div className="rounded-lg border border-gray-200 p-6">
            <h2 className="mb-4 block text-lg font-semibold text-gray-700">② 価値算定パラメータ</h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
              <div>
                <label htmlFor="engine_per_kg" className="block text-sm font-medium text-gray-700">エンジン単価 (円/kg)</label>
                <input type="number" step="0.1" name="engine_per_kg" value={params.engine_per_kg} onChange={handleParamChange} className="mt-1 block w-full rounded-md border-gray-300 p-2 shadow-sm" />
              </div>
              <div>
                <label htmlFor="press_per_kg" className="block text-sm font-medium text-gray-700">プレス単価 (円/kg)</label>
                <input type="number" step="0.1" name="press_per_kg" value={params.press_per_kg} onChange={handleParamChange} className="mt-1 block w-full rounded-md border-gray-300 p-2 shadow-sm" />
              </div>
              <div>
                <label htmlFor="kouzan_per_kg" className="block text-sm font-medium text-gray-700">甲山単価 (円/kg)</label>
                <input type="number" step="0.1" name="kouzan_per_kg" value={params.kouzan_per_kg} onChange={handleParamChange} className="mt-1 block w-full rounded-md border-gray-300 p-2 shadow-sm" />
              </div>
              <div>
                <label htmlFor="harness_per_kg" className="block text-sm font-medium text-gray-700">ハーネス単価 (円/kg)</label>
                <input type="number" step="0.1" name="harness_per_kg" value={params.harness_per_kg} onChange={handleParamChange} className="mt-1 block w-full rounded-md border-gray-300 p-2 shadow-sm" />
              </div>
              <div>
                <label htmlFor="aluminum_wheels_price" className="block text-sm font-medium text-gray-700">アルミホイール (円)</label>
                <input type="number" name="aluminum_wheels_price" value={params.aluminum_wheels_price} onChange={handleParamChange} className="mt-1 block w-full rounded-md border-gray-300 p-2 shadow-sm" />
              </div>
              <div>
                <label htmlFor="catalyst_price" className="block text-sm font-medium text-gray-700">触媒 (円)</label>
                <input type="number" name="catalyst_price" value={params.catalyst_price} onChange={handleParamChange} className="mt-1 block w-full rounded-md border-gray-300 p-2 shadow-sm" />
              </div>
              <div>
                <label htmlFor="transport_cost" className="block text-sm font-medium text-gray-700">輸送費等諸経費 (円)</label>
                <input type="number" name="transport_cost" value={params.transport_cost} onChange={handleParamChange} className="mt-1 block w-full rounded-md border-gray-300 p-2 shadow-sm" />
              </div>
            </div>
          </div>

          <button type="submit" disabled={!file || loading} className="w-full rounded-lg bg-blue-600 px-4 py-3 text-base font-bold text-white shadow-md hover:bg-blue-700 disabled:bg-gray-400">
            {loading ? '処理中...' : '価値を算定してレポート出力'}
          </button>
        </form>
      </div>
    </main>
  )
}