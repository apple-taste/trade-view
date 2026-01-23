import { useEffect, useMemo, useRef, useState } from 'react';
import axios from 'axios';
import { useLocation, useNavigate } from 'react-router-dom';
import { useJojoModal } from '../components/JojoModal';

type BillingStatus = {
  billing_enabled: boolean;
  is_paid: boolean;
  paid_until?: string | null;
  plan?: string | null;
};

type PaymentOrderItem = {
  order_no: string;
  user_id: number;
  channel: string;
  amount_cents: number;
  currency: string;
  plan: string;
  months: number;
  status: string;
  note?: string | null;
  approved_by_admin?: string | null;
  approved_at?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
};

type PaymentQrs = {
  wechat_pay_qr_url?: string | null;
  alipay_pay_qr_url?: string | null;
  receiver_note?: string | null;
};

type BillingPricing = {
  plan: string;
  months: number;
  unit_price_cents: number;
  amount_cents: number;
  currency: string;
};

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

export default function Billing() {
  const navigate = useNavigate();
  const location = useLocation();
  const { confirm, Modal } = useJojoModal();

  const [billingStatus, setBillingStatus] = useState<BillingStatus | null>(null);
  const [paymentQrs, setPaymentQrs] = useState<PaymentQrs | null>(null);
  const [pricing, setPricing] = useState<BillingPricing | null>(null);
  const [activeOrder, setActiveOrder] = useState<PaymentOrderItem | null>(null);
  const [paymentNote, setPaymentNote] = useState('');
  const [creatingOrder, setCreatingOrder] = useState(false);
  const [savingNote, setSavingNote] = useState(false);
  const [checking, setChecking] = useState(false);
  const abortRef = useRef(false);

  const months = useMemo(() => {
    const qs = new URLSearchParams(location.search);
    const raw = Number(qs.get('months') || 1);
    return Number.isFinite(raw) && raw > 0 ? Math.floor(raw) : 1;
  }, [location.search]);

  useEffect(() => {
    abortRef.current = false;
    return () => {
      abortRef.current = true;
    };
  }, []);

  const fetchBillingStatus = async () => {
    try {
      const res = await axios.get('/api/user/billing-status');
      setBillingStatus(res.data);
    } catch {
      setBillingStatus(null);
    }
  };

  const fetchPaymentQrs = async () => {
    try {
      const res = await axios.get('/api/user/payment-qrs');
      setPaymentQrs(res.data);
    } catch {
      setPaymentQrs(null);
    }
  };

  const fetchPricing = async () => {
    try {
      const res = await axios.get('/api/user/billing-plans/pro/price', { params: { months } });
      setPricing(res.data);
    } catch {
      setPricing(null);
    }
  };

  useEffect(() => {
    fetchBillingStatus();
    fetchPaymentQrs();
  }, []);

  useEffect(() => {
    fetchPricing();
  }, [months]);

  const createOrder = async (channel: 'wechat' | 'alipay') => {
    setCreatingOrder(true);
    try {
      const res = await axios.post('/api/user/payment-orders', { channel, plan: 'pro', months });
      const order = res.data?.order as PaymentOrderItem | undefined;
      const instructions = String(res.data?.instructions || '').trim();
      if (!order?.order_no) {
        await confirm('创建失败', '订单创建失败，请稍后重试');
        return;
      }
      setActiveOrder(order);
      await confirm('订单已创建', instructions || `订单号：${order.order_no}`);
    } catch (error: any) {
      await confirm('创建失败', error.response?.data?.detail || error.message || '创建失败');
    } finally {
      setCreatingOrder(false);
    }
  };

  const savePaymentNote = async () => {
    if (!activeOrder?.order_no) {
      await confirm('没有订单', '请先创建订单');
      return;
    }
    const note = paymentNote.trim();
    if (!note) {
      await confirm('备注为空', '请输入付款备注（例如：已付款/转账时间/手机号尾号等）');
      return;
    }
    setSavingNote(true);
    try {
      const res = await axios.patch(`/api/user/payment-orders/${activeOrder.order_no}/note`, { note });
      setActiveOrder(res.data as PaymentOrderItem);
      setPaymentNote('');
      await confirm('已提交', '备注已提交，等待审核');
    } catch (error: any) {
      await confirm('提交失败', error.response?.data?.detail || error.message || '提交失败');
    } finally {
      setSavingNote(false);
    }
  };

  const checkUntilApproved = async () => {
    if (!activeOrder?.order_no) {
      await confirm('没有订单', '请先创建订单');
      return;
    }
    setChecking(true);
    try {
      const deadline = Date.now() + 3 * 60_000;
      while (!abortRef.current && Date.now() < deadline) {
        const res = await axios.get(`/api/user/payment-orders/${activeOrder.order_no}`);
        const next = res.data as PaymentOrderItem;
        setActiveOrder(next);
        if (String(next.status).toLowerCase() === 'approved') {
          await fetchBillingStatus();
          await confirm('开通成功', '已确认支付成功并开通会员');
          navigate('/');
          return;
        }
        await sleep(3000);
      }
      if (!abortRef.current) {
        await confirm('尚未开通', '订单仍在待审核状态，请稍后再点“检查开通状态”');
      }
    } catch (error: any) {
      await confirm('查询失败', error.response?.data?.detail || error.message || '查询失败');
    } finally {
      setChecking(false);
    }
  };

  return (
    <>
      <div className="min-h-screen bg-gray-900 text-gray-200 p-4">
        <div className="jojo-card p-4 max-w-3xl mx-auto">
          <div className="flex items-center justify-between mb-3">
            <h1 className="jojo-title text-2xl">会员开通</h1>
            <button onClick={() => navigate(-1)} className="jojo-button text-xs px-3 py-2">
              返回
            </button>
          </div>

          <div className="bg-gray-800/50 px-3 py-2 rounded border border-gray-700 text-sm">
            <div className="flex flex-wrap gap-x-4 gap-y-1">
              <span>套餐：{billingStatus?.plan || '-'}</span>
              <span>到期：{billingStatus?.paid_until || '-'}</span>
              <span>状态：{billingStatus?.is_paid ? '已开通' : '未开通'}</span>
            </div>
          </div>

          {!billingStatus?.billing_enabled ? (
            <div className="mt-3 bg-gray-800/50 px-3 py-3 rounded border border-gray-700 text-sm text-gray-300">
              当前未开启收费，无法开通会员
            </div>
          ) : null}

          <div className="mt-3 bg-gray-800/50 px-3 py-2 rounded border border-gray-700 text-sm text-gray-300">
            价格：
            {pricing?.unit_price_cents != null
              ? ` pro 月费 ¥${(Number(pricing.unit_price_cents) / 100).toFixed(2)}，${months} 个月合计 ¥${(Number(pricing.amount_cents) / 100).toFixed(2)}`
              : ' -'}
          </div>

          <div className="mt-3 grid grid-cols-1 md:grid-cols-2 gap-2">
            <button
              onClick={() => createOrder('wechat')}
              className="w-full px-4 py-3 bg-jojo-purple/50 hover:bg-jojo-purple border-2 border-jojo-gold/50 hover:border-jojo-gold rounded-lg text-jojo-gold font-semibold text-sm transition-all shadow-lg disabled:opacity-50"
              disabled={creatingOrder || checking || !billingStatus?.billing_enabled}
            >
              微信支付开通（{months} 个月）
            </button>
            <button
              onClick={() => createOrder('alipay')}
              className="w-full px-4 py-3 bg-jojo-purple/50 hover:bg-jojo-purple border-2 border-jojo-gold/50 hover:border-jojo-gold rounded-lg text-jojo-gold font-semibold text-sm transition-all shadow-lg disabled:opacity-50"
              disabled={creatingOrder || checking || !billingStatus?.billing_enabled}
            >
              支付宝开通（{months} 个月）
            </button>
          </div>

          <div className="mt-3 grid grid-cols-1 md:grid-cols-2 gap-2">
            <div className="bg-gray-900/50 px-3 py-2 rounded border border-gray-800">
              <div className="text-xs text-gray-400 mb-1">微信收款码</div>
              {paymentQrs?.wechat_pay_qr_url ? (
                <img
                  src={paymentQrs.wechat_pay_qr_url}
                  alt="wechat-qr"
                  className="w-40 h-40 object-contain bg-gray-950 rounded"
                />
              ) : (
                <div className="w-40 h-40 flex items-center justify-center text-xs text-gray-500 bg-gray-950 rounded">未配置</div>
              )}
            </div>
            <div className="bg-gray-900/50 px-3 py-2 rounded border border-gray-800">
              <div className="text-xs text-gray-400 mb-1">支付宝收款码</div>
              {paymentQrs?.alipay_pay_qr_url ? (
                <img
                  src={paymentQrs.alipay_pay_qr_url}
                  alt="alipay-qr"
                  className="w-40 h-40 object-contain bg-gray-950 rounded"
                />
              ) : (
                <div className="w-40 h-40 flex items-center justify-center text-xs text-gray-500 bg-gray-950 rounded">未配置</div>
              )}
            </div>
          </div>

          {paymentQrs?.receiver_note ? (
            <div className="mt-2 text-sm text-gray-300 whitespace-pre-wrap bg-gray-800/50 px-3 py-2 rounded border border-gray-700">
              {paymentQrs.receiver_note}
            </div>
          ) : null}

          {activeOrder ? (
            <div className="mt-3 bg-gray-900/50 px-3 py-3 rounded border border-gray-800">
              <div className="text-sm text-gray-300 mb-2">
                当前订单：<span className="font-mono">{activeOrder.order_no}</span>（{activeOrder.channel === 'wechat' ? '微信' : '支付宝'}）
              </div>
              <div className="text-sm text-gray-300 mb-2">
                金额：¥{(Number(activeOrder.amount_cents || 0) / 100).toFixed(2)}，状态：{activeOrder.status}
              </div>

              <div className="grid grid-cols-1 md:grid-cols-[1fr_auto] gap-2">
                <input
                  value={paymentNote}
                  onChange={(e) => setPaymentNote(e.target.value)}
                  placeholder="提交付款备注（转账附言/时间/手机号尾号等）"
                  className="w-full px-3 py-2 rounded bg-gray-950 border border-gray-700 text-white text-sm"
                  disabled={savingNote || checking}
                />
                <button
                  onClick={savePaymentNote}
                  className="px-3 py-2 rounded bg-jojo-purple/50 hover:bg-jojo-purple border-2 border-jojo-gold/50 hover:border-jojo-gold text-jojo-gold font-semibold text-sm transition-all shadow-lg disabled:opacity-50"
                  disabled={savingNote || checking}
                >
                  {savingNote ? '提交中…' : '提交备注'}
                </button>
              </div>

              <div className="mt-2">
                <button
                  onClick={checkUntilApproved}
                  className="jojo-button w-full py-2"
                  disabled={checking}
                >
                  {checking ? '检查中…' : '我已完成支付，检查开通状态'}
                </button>
              </div>
            </div>
          ) : (
            <div className="mt-3 bg-gray-800/50 px-3 py-3 rounded border border-gray-700 text-sm text-gray-300">
              先选择微信或支付宝创建订单，再扫码支付
            </div>
          )}
        </div>
      </div>
      <Modal />
    </>
  );
}
