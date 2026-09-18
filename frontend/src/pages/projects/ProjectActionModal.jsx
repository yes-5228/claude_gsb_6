import { useState } from 'react';

import Field from '../../components/Field.jsx';
import Modal from '../../components/Modal.jsx';
import { StatusTag } from '../../components/Tags.jsx';

const PLACEHOLDER = {
  施工中: '如：施工队进场，围挡封闭，公厕暂停使用',
  待验收: '填写完工情况，如：全部工程完工，申请竣工验收',
  已验收: '填写竣工验收意见，如：工程质量合格、资料齐全，同意恢复开放',
};

export default function ProjectActionModal({ option, project, onClose, onSubmit, saving }) {
  const [operator, setOperator] = useState(project.project_manager || '');
  const [remark, setRemark] = useState('');
  const [actualCost, setActualCost] = useState(
    project.budget ? String(project.budget) : '',
  );

  const isAccept = option.status === '已验收';

  const submit = (event) => {
    event.preventDefault();
    if (!operator.trim()) return;
    onSubmit({
      to_status: option.status,
      operator: operator.trim(),
      remark: remark || null,
      actual_cost: isAccept && actualCost !== '' ? Number(actualCost) : null,
    });
  };

  return (
    <Modal
      title={`项目流转 - ${option.action}`}
      onClose={onClose}
      footer={
        <>
          <button type="button" className="btn" onClick={onClose}>
            取消
          </button>
          <button type="submit" form="project-action" className="btn btn-primary" disabled={saving}>
            {saving ? '提交中...' : '确认提交'}
          </button>
        </>
      }
    >
      <div className="alert alert-info">
        当前状态 <StatusTag status={project.status} /> 变更为 <StatusTag status={option.status} />
        {isAccept ? '，验收通过后公厕将恢复立项前状态，项目档案封存' : ''}
      </div>
      <form id="project-action" className="form-grid" onSubmit={submit}>
        <Field label="操作人 *">
          <input value={operator} onChange={(event) => setOperator(event.target.value)} placeholder="如：现场负责人 / 验收组" />
        </Field>
        {isAccept ? (
          <Field label="结算造价（万元）">
            <input
              type="number"
              min="0"
              step="0.1"
              value={actualCost}
              onChange={(event) => setActualCost(event.target.value)}
            />
          </Field>
        ) : null}
        <Field label="处理说明" full>
          <textarea
            rows="3"
            value={remark}
            onChange={(event) => setRemark(event.target.value)}
            placeholder={PLACEHOLDER[option.status] || '填写本次处理说明'}
          />
        </Field>
      </form>
    </Modal>
  );
}
