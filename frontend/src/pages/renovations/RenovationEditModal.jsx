import { useState } from 'react';

import { renovationApi } from '../../api/renovations.js';
import Field from '../../components/Field.jsx';
import Modal from '../../components/Modal.jsx';
import { useToast } from '../../components/Toast.jsx';
import { toDateTimeInput } from '../../utils/format.js';

export default function RenovationEditModal({ project, onClose, onSaved }) {
  const toast = useToast();
  const [form, setForm] = useState({
    title: project.title,
    reason: project.reason || '',
    contractor: project.contractor || '',
    planned_start: project.planned_start ? toDateTimeInput(project.planned_start) : '',
    planned_end: project.planned_end ? toDateTimeInput(project.planned_end) : '',
    budget: project.budget,
    remark: project.remark || '',
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  const setValue = (key) => (event) =>
    setForm((prev) => ({ ...prev, [key]: event.target.value }));

  const submit = async (event) => {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await renovationApi.update(project.id, {
        title: form.title,
        reason: form.reason,
        contractor: form.contractor,
        planned_start: form.planned_start ? new Date(form.planned_start).toISOString() : null,
        planned_end: form.planned_end ? new Date(form.planned_end).toISOString() : null,
        budget: form.budget === '' ? 0 : Number(form.budget),
        remark: form.remark || null,
      });
      toast.success('项目信息已更新');
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
      title={`编辑项目 - ${project.code}`}
      onClose={onClose}
      width={720}
      footer={
        <>
          <button type="button" className="btn" onClick={onClose}>
            取消
          </button>
          <button
            type="submit"
            form="renovation-edit"
            className="btn btn-primary"
            disabled={saving}
          >
            保存
          </button>
        </>
      }
    >
      {error ? <div className="alert alert-error">{error}</div> : null}
      <form id="renovation-edit" className="form-grid" onSubmit={submit}>
        <Field label="项目名称" full>
          <input value={form.title} onChange={setValue('title')} />
        </Field>
        <Field label="改造事由" full>
          <textarea rows="2" value={form.reason} onChange={setValue('reason')} />
        </Field>
        <Field label="施工单位">
          <input value={form.contractor} onChange={setValue('contractor')} />
        </Field>
        <Field label="预算（万元）">
          <input
            type="number"
            min="0"
            step="0.01"
            value={form.budget}
            onChange={setValue('budget')}
          />
        </Field>
        <Field label="计划开工">
          <input
            type="datetime-local"
            value={form.planned_start}
            onChange={setValue('planned_start')}
          />
        </Field>
        <Field label="计划完工">
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
