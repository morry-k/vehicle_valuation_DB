// frontend/app/page.tsx
'use client'

import { useState } from 'react'

export default function Home() {
  const [file, setFile] = useState<File | null>(null)
  const [params, setParams] = useState({
    press_per_kg: 25.5,
    kouzan_per_kg: 35.0,
    transport_cost: 5000,
  })

  // パラメータが変更されたときの処理
  const handleParamChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target
    setParams(prev => ({ ...prev, [name]: Number(value) }))
  }

  // フォームが送信されたときの処理
  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    if (!file) {
      alert('PDFファイルを選択してください。')
      return
    }
    
    console.log("送信するファイル:", file)
    console.log("送信するパラメータ:", params)
    
    // 次のステップで、ここにFastAPIサーバーへデータを送信する処理を追加します
    alert('データ送信の準備ができました！')
  }

  return (
    <main className="container mx-auto p-8">
      <h1 className="text-3xl font-bold mb-6">車両価値算定ツール</h1>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* 1. PDFアップロード機能 */}
        <div className="p-6 border rounded-lg">
          <h2 className="text-xl font-semibold mb-3">① オークション出品票PDF</h2>
          <input
            type="file"
            accept="application/pdf"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
            className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
          />
        </div>

        {/* 2. パラメータ入力エリア */}
        <div className="p-6 border rounded-lg">
          <h2 className="text-xl font-semibold mb-3">② 価値算定パラメータ</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label htmlFor="press_per_kg" className="block text-sm font-medium text-gray-700">プレス単価 (円/kg)</label>
              <input
                type="number"
                name="press_per_kg"
                id="press_per_kg"
                value={params.press_per_kg}
                onChange={handleParamChange}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm p-2"
              />
            </div>
            <div>
              <label htmlFor="kouzan_per_kg" className="block text-sm font-medium text-gray-700">甲山単価 (円/kg)</label>
              <input
                type="number"
                name="kouzan_per_kg"
                id="kouzan_per_kg"
                value={params.kouzan_per_kg}
                onChange={handleParamChange}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm p-2"
              />
            </div>
            <div>
              <label htmlFor="transport_cost" className="block text-sm font-medium text-gray-700">輸送費 (円)</label>
              <input
                type="number"
                name="transport_cost"
                id="transport_cost"
                value={params.transport_cost}
                onChange={handleParamChange}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm p-2"
              />
            </div>
          </div>
        </div>

        {/* 3. 実行ボタン */}
        <button
          type="submit"
          className="w-full bg-blue-600 text-white font-bold py-3 px-4 rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:bg-gray-400"
          disabled={!file}
        >
          価値を算定してレポート出力
        </button>
      </form>
    </main>
  )
}