import { useMemo, useState, type ChangeEvent } from 'react';
import { useForex } from '../../contexts/ForexContext';
import { useLocale } from '../../contexts/LocaleContext';
import { useTrade } from '../../contexts/TradeContext';
import { Settings, X, Save } from 'lucide-react';

export default function ForexSettingsModal({ onClose }: { onClose: () => void }) {
  const { account, saveSettings } = useForex();
  const { t } = useLocale();
  const { effectiveForexStrategyId } = useTrade();
  const [currency, setCurrency] = useState(account.currency);
  const [leverage, setLeverage] = useState(String(account.leverage || 100));
  const [initialBalance, setInitialBalance] = useState(String(account.initialBalance || account.balance));
  const [initialDate, setInitialDate] = useState<string>(account.initialDate ? String(account.initialDate) : '');

  const leverageOptions = useMemo(() => ['1', '10', '50', '100', '200', '400', '500', '1000'], []);
  
  const handleChange = (e: ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    if (name === 'currency') setCurrency(value);
    if (name === 'leverage') setLeverage(value);
    if (name === 'initialBalance') setInitialBalance(value);
    if (name === 'initialDate') setInitialDate(value);
  };

  const handleSave = async () => {
    try {
      if (effectiveForexStrategyId == null) {
        alert('请先创建并选择一个策略，然后再保存设置！');
        return;
      }
      const balance = Number(initialBalance);
      if (!Number.isFinite(balance) || balance < 0) throw new Error('Invalid balance');
      const payload = {
        currency,
        leverage: Number(leverage),
        initial_balance: balance,
        initial_date: initialDate || undefined,
      };
      onClose();
      saveSettings(payload).catch((err: any) => {
        alert(err?.response?.data?.detail || err?.message || '操作失败');
      });
    } catch (err: any) {
      alert(err?.response?.data?.detail || err?.message || '操作失败');
    }
  };

  return (
    <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4">
      <div className="bg-gray-800 rounded-lg shadow-2xl w-full max-w-2xl border border-gray-700 max-h-[90vh] overflow-y-auto custom-scrollbar">
        <div className="p-4 border-b border-gray-700 flex justify-between items-center bg-gray-900 sticky top-0">
          <h2 className="text-xl font-bold text-jojo-gold flex items-center gap-2">
            <Settings size={20} />
            {t('forex.brokerSettings')}
          </h2>
          <button onClick={onClose} className="text-gray-400 hover:text-white">
            <X size={20} />
          </button>
        </div>

        <div className="p-6 space-y-6 text-gray-200">
          <div className="space-y-4">
            <h3 className="text-lg font-semibold text-blue-400 border-b border-gray-700 pb-2">{t('forex.generalSettings')}</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm text-gray-400 mb-1">{t('forex.accountCurrency')}</label>
                <select
                  name="currency"
                  value={currency}
                  onChange={handleChange}
                  className="w-full bg-gray-900 border border-gray-600 rounded px-3 py-2 focus:border-blue-500 outline-none"
                >
                  <option value="USD">USD</option>
                  <option value="EUR">EUR</option>
                  <option value="GBP">GBP</option>
                  <option value="JPY">JPY</option>
                </select>
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-1">{t('forex.leverage')} (1:X)</label>
                <select
                  name="leverage"
                  value={leverage}
                  onChange={handleChange}
                  className="w-full bg-gray-900 border border-gray-600 rounded px-3 py-2 focus:border-blue-500 outline-none"
                >
                  {leverageOptions.map((v) => (
                    <option key={v} value={v}>1:{v}</option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          <div className="space-y-4">
            <h3 className="text-lg font-semibold text-blue-400 border-b border-gray-700 pb-2">资金锚点</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm text-gray-400 mb-1">{t('forex.initialBalance')}</label>
                <input
                  type="number"
                  name="initialBalance"
                  value={initialBalance}
                  onChange={handleChange}
                  className="w-full bg-gray-900 border border-gray-600 rounded px-3 py-2 focus:border-blue-500 outline-none"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-1">{t('forex.initialDate')}</label>
                <input
                  type="date"
                  name="initialDate"
                  value={initialDate}
                  onChange={handleChange}
                  className="w-full bg-gray-900 border border-gray-600 rounded px-3 py-2 focus:border-blue-500 outline-none"
                />
              </div>
            </div>
          </div>

        </div>

        <div className="p-4 border-t border-gray-700 bg-gray-900 flex justify-end">
          <div className="flex gap-2">
            <button
              onClick={onClose}
              className="px-4 py-2 text-gray-400 hover:text-white transition-colors"
            >
              {t('forex.cancel')}
            </button>
            <button
              onClick={handleSave}
              className="flex items-center gap-2 px-6 py-2 bg-jojo-gold text-gray-900 font-bold rounded hover:bg-yellow-400 transition-colors shadow-lg shadow-yellow-500/20"
            >
              <Save size={18} />
              {t('forex.save')}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
