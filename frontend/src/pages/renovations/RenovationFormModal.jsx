import { useEffect, useState } from 'react';

import { metaApi } from '../../api/meta.js';
import { renovationApi } from '../../api/renovations.js';
import Field from '../../components/Field.jsx';
import Modal from '../../components/Modal.jsx';
import { useToast } from '../../components/Toast.jsx';
import { toDateTimeInput } from '../../utils/format.js';

export default function RenovationFormModal({ defaultRestroomId, onClose, onSaved }) {
  const toast = useToast();
  const [restrooms, setRestrooms] = useState([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [form, setForm] = useState({
    restroom_id: defaultRestroomId ? Number(defaultRestroomId) : '',
    title: '',
    reason: '',
    approved_at: toDateTimeInput(new Date()),
    contractor: '',
    planned_start: toDateTimeInput(new Date()),
    planned_end: toDateTimeInput(new Date(Date.now() + 30 * 24 * 3600 * 1000)),
    budget: '',
    remark: '',
  });

  useEffect(() => {
    metaApi
      .restroomOptions()
      .then(setRestrooms)
      .catch((err) => setError(err.message));
  }, []);

  const setValue = (key) => (event) =>
    setForm((prev) => ({ ...prev, [key]: event.target.value }));

  const submit = async (event) => {
    event.preventDefault();
    if (!form.restroom_id) {
      setError('请选择所属公厕');
      return;
    }
    if (!form.title.trim()) {
      setError('请填写项目名称');
      return;
    }
    if (!form.reason.trim()) {
      setError('请填写改造事由');
      return;
    }
    if (!form.contractor.trim()) {
      setError('请填写施工单位');
      return;
    }
    if (!form.planned_start || !form.planned_end) {
      setError('请填写计划工期');
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await renovationApi.create({
        restroom_id: Number(form.restroom_id),
        title: form.title.trim(),
        reason: form.reason.trim(),
        approved_at: form.approved_at ? new Date(form.approved_at).toISOString() : null,
        contractor: form.contractor.trim(),
        planned_start: new Date(form.planned_start).toISOString(),
        planned_end: new Date(form.planned_end).toISOString(),
        budget: form.budget === '' ? 0 : Number(form.budget),
        remark: form.remark || null,
      });
      toast.success('项目已立项登记');
      onSaved();
      onClose();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal
      title="改造项目立项登记"
      onClose={onClose}
      width={780}
      footer={
        <>
          <button type="button" className="btn" onClick={onClose}>
            取消
          </button>
          <button
            type="submit"
            form="renovation-form"
            className="btn btn-primary"
            disabled={saving}
          >
            {saving ? '提交中...' : '确认立项'}
          </button>
        </>
      }
    >
      {error ? <div className="alert alert-error">{error}</div> : null}
      <form id="renovation-form" className="form-grid" onSubmit={submit}>
        <Field label="所属公厕 *" hint="同一公厕同一时间只允许一个进行中的改造项目">
          <select value={form.restroom_id} onChange={setValue('restroom_id')}>
            <option value="">请选择公厕</option>
            {restrooms.map((item) => (
              <option key={item.id} value={item.id}>
                {item.code} {item.name}（{item.district}）
              </option>
            ))}
          </select>
        </Field>
        <Field label="立项时间">
          <input
            type="datetime-local"
            value={form.approved_at}
            onChange={setValue('approved_at')}
          />
        </Field>
        <Field label="项目名称 *" full>
          <input
            value={form.title}
            onChange={setValue('title')}
            placeholder="如：无障碍设施提升改造"
          />
        </Field>
        <Field label="改造事由 *" full>
          <textarea
            rows="2"
            value={form.reason}
            onChange={setValue('reason')}
            placeholder="改造的背景与原因，将写入项目档案"
          />
        </Field>
        <Field label="施工单位 *">
          <input
            value={form.contractor}
            onChange={setValue('contractor')}
            placeholder="如：市政工程一公司"
          />
        </Field>
        <Field label="预算（万元）">
          <input
            type="number"
            min="0"
            step="0.01"
            value={form.budget}
            onChange={setValue('budget')}
            placeholder="0.00"
          />
        </Field>
        <Field label="计划开工 *">
          <input
            type="datetime-local"
            value={form.planned_start}
            onChange={setValue('planned_start')}
          />
        </Field>
        <Field label="计划完工 *">
          <input
            type="datetime-local"
            value={form.planned_end}
            onChange={setValue('planned_end')}
          />
        </Field>
        <Field label="备注" full>
          <textarea rows="2" value={form.remark} onChange={setValue('remark')} />
        </Field>
      </form>
    </Modal>
  );
}
