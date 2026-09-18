import { useEffect, useState } from 'react';

import { metaApi } from '../../api/meta.js';
import { projectApi } from '../../api/projects.js';
import Field from '../../components/Field.jsx';
import Modal from '../../components/Modal.jsx';
import { useToast } from '../../components/Toast.jsx';
import { toDateTimeInput } from '../../utils/format.js';

export default function ProjectFormModal({ onClose, onSaved }) {
  const toast = useToast();
  const [restrooms, setRestrooms] = useState([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [form, setForm] = useState({
    restroom_id: '',
    reason: '',
    construction_unit: '',
    project_manager: '',
    contact_phone: '',
    setup_time: toDateTimeInput(new Date()),
    planned_start_date: '',
    planned_end_date: '',
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
      setError('请选择改造公厕');
      return;
    }
    if (!form.reason.trim()) {
      setError('请填写改造事由');
      return;
    }
    if (form.planned_start_date && form.planned_end_date
      && form.planned_end_date < form.planned_start_date) {
      setError('计划完工日期不能早于计划开工日期');
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await projectApi.create({
        restroom_id: Number(form.restroom_id),
        reason: form.reason.trim(),
        construction_unit: form.construction_unit.trim(),
        project_manager: form.project_manager.trim(),
        contact_phone: form.contact_phone.trim(),
        setup_time: form.setup_time ? new Date(form.setup_time).toISOString() : null,
        planned_start_date: form.planned_start_date || null,
        planned_end_date: form.planned_end_date || null,
        budget: form.budget === '' ? 0 : Number(form.budget),
        remark: form.remark || null,
      });
      toast.success('立项成功，改造期间公厕已自动暂停使用');
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
          <button type="submit" form="project-form" className="btn btn-primary" disabled={saving}>
            {saving ? '提交中...' : '确认立项'}
          </button>
        </>
      }
    >
      <div className="alert alert-info">
        立项成功后，所选公厕将自动转为「暂停使用」，直至竣工验收通过后恢复立项前状态。
      </div>
      {error ? <div className="alert alert-error">{error}</div> : null}
      <form id="project-form" className="form-grid" onSubmit={submit}>
        <Field label="改造公厕 *">
          <select value={form.restroom_id} onChange={setValue('restroom_id')}>
            <option value="">请选择公厕</option>
            {restrooms.map((item) => (
              <option key={item.id} value={item.id}>
                {item.code} {item.name}（{item.district}）
              </option>
            ))}
          </select>
        </Field>
        <Field label="施工单位">
          <input value={form.construction_unit} onChange={setValue('construction_unit')} placeholder="如：城央建设工程有限公司" />
        </Field>
        <Field label="改造事由 *" full>
          <textarea
            rows="3"
            value={form.reason}
            onChange={setValue('reason')}
            placeholder="如：设施老化渗漏，按一类公厕标准整体提档升级"
          />
        </Field>
        <Field label="现场负责人">
          <input value={form.project_manager} onChange={setValue('project_manager')} />
        </Field>
        <Field label="联系电话">
          <input value={form.contact_phone} onChange={setValue('contact_phone')} />
        </Field>
        <Field label="立项时间">
          <input type="datetime-local" value={form.setup_time} onChange={setValue('setup_time')} />
        </Field>
        <Field label="预算金额（万元）">
          <input
            type="number"
            min="0"
            step="0.1"
            value={form.budget}
            onChange={setValue('budget')}
          />
        </Field>
        <Field label="计划开工日期">
          <input type="date" value={form.planned_start_date} onChange={setValue('planned_start_date')} />
        </Field>
        <Field label="计划完工日期">
          <input type="date" value={form.planned_end_date} onChange={setValue('planned_end_date')} />
        </Field>
        <Field label="备注" full>
          <textarea rows="2" value={form.remark} onChange={setValue('remark')} />
        </Field>
      </form>
    </Modal>
  );
}
