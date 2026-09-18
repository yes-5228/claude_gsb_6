import { useState } from 'react';

import Field from '../../components/Field.jsx';
import Modal from '../../components/Modal.jsx';

function today() {
  const date = new Date();
  const pad = (num) => String(num).padStart(2, '0');
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

/**
 * 进度节点相关弹窗：
 * - mode="create"：登记进度节点
 * - mode="accept"：登记/复验节点阶段验收结论
 */
export default function NodeFormModal({ mode, node, project, onClose, onSubmit, saving }) {
  const isAccept = mode === 'accept';
  const [form, setForm] = useState(
    isAccept
      ? {
          result: node?.acceptance_result || '合格',
          opinion: node?.acceptance_opinion || '',
          acceptor: node?.acceptor || '',
        }
      : {
          title: '',
          node_date: today(),
          progress: '',
          progress_percent: '',
          operator: project?.project_manager || '',
        },
  );
  const [error, setError] = useState(null);

  const setValue = (key) => (event) =>
    setForm((prev) => ({ ...prev, [key]: event.target.value }));

  const submit = (event) => {
    event.preventDefault();
    if (isAccept) {
      if (!form.acceptor.trim()) {
        setError('请填写验收人');
        return;
      }
      onSubmit({ result: form.result, opinion: form.opinion || null, acceptor: form.acceptor.trim() });
      return;
    }
    if (!form.title.trim()) {
      setError('请填写节点名称');
      return;
    }
    if (!form.node_date) {
      setError('请选择节点日期');
      return;
    }
    onSubmit({
      title: form.title.trim(),
      node_date: form.node_date,
      progress: form.progress,
      progress_percent: form.progress_percent === '' ? null : Number(form.progress_percent),
      operator: form.operator.trim(),
    });
  };

  return (
    <Modal
      title={isAccept ? `阶段验收 - ${node?.title || ''}` : '登记改造进度节点'}
      onClose={onClose}
      width={isAccept ? 560 : 680}
      footer={
        <>
          <button type="button" className="btn" onClick={onClose}>
            取消
          </button>
          <button type="submit" form="node-form" className="btn btn-primary" disabled={saving}>
            {saving ? '提交中...' : '确认提交'}
          </button>
        </>
      }
    >
      {error ? <div className="alert alert-error">{error}</div> : null}
      <form id="node-form" className="form-grid" onSubmit={submit}>
        {isAccept ? (
          <>
            <Field label="验收结论 *">
              <select value={form.result} onChange={setValue('result')}>
                <option value="合格">合格</option>
                <option value="不合格">不合格</option>
              </select>
            </Field>
            <Field label="验收人 *">
              <input value={form.acceptor} onChange={setValue('acceptor')} placeholder="如：监理吴工 / 甲方代表" />
            </Field>
            <Field label="验收意见" full>
              <textarea
                rows="3"
                value={form.opinion}
                onChange={setValue('opinion')}
                placeholder="如：试压合格、安装规范；复验时将覆盖原结论"
              />
            </Field>
          </>
        ) : (
          <>
            <Field label="节点名称 *">
              <input value={form.title} onChange={setValue('title')} placeholder="如：水电管线改造" />
            </Field>
            <Field label="节点日期 *">
              <input type="date" value={form.node_date} onChange={setValue('node_date')} />
            </Field>
            <Field label="完成度（%）">
              <input
                type="number"
                min="0"
                max="100"
                value={form.progress_percent}
                onChange={setValue('progress_percent')}
              />
            </Field>
            <Field label="填报人">
              <input value={form.operator} onChange={setValue('operator')} />
            </Field>
            <Field label="进度说明" full>
              <textarea
                rows="3"
                value={form.progress}
                onChange={setValue('progress')}
                placeholder="本节点完成的实物量、质量与安全情况"
              />
            </Field>
          </>
        )}
      </form>
    </Modal>
  );
}
