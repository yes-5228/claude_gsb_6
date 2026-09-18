import { useState } from 'react';

import Field from '../../components/Field.jsx';
import Modal from '../../components/Modal.jsx';
import { StatusTag } from '../../components/Tags.jsx';
import { useDictionaries } from '../../hooks/useDictionaries.js';

const PLACEHOLDER = {
  改造中: '填写开工说明，如：施工围挡已搭设，正式进场',
  待完工验收: '填写申请说明，如：合同范围内工程全部完成',
  已完工: '填写验收意见，如：现场验收合格，同意恢复开放',
  已取消: '填写取消原因，如：资金未落实，暂缓实施',
};

export default function RenovationActionModal({ option, project, onClose, onSubmit, saving }) {
  const { dictionaries } = useDictionaries();
  const [operator, setOperator] = useState('');
  const [conclusion, setConclusion] = useState('通过');
  const [remark, setRemark] = useState('');

  const isCompletion = option.status === '已完工';

  const submit = (event) => {
    event.preventDefault();
    if (!operator.trim()) return;
    onSubmit({
      to_status: option.status,
      operator: operator.trim(),
      conclusion: isCompletion ? conclusion : null,
      remark: remark || null,
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
          <button
            type="submit"
            form="renovation-action"
            className="btn btn-primary"
            disabled={saving}
          >
            {saving ? '提交中...' : '确认提交'}
          </button>
        </>
      }
    >
      <div className="alert alert-info">
        当前状态 <StatusTag status={project.status} /> 变更为 <StatusTag status={option.status} />
        {option.status === '改造中' && project.status === '已立项'
          ? '，公厕将自动转为「暂停使用」'
          : null}
        {isCompletion ? '，公厕将恢复开放' : null}
      </div>
      <form id="renovation-action" className="form-grid" onSubmit={submit}>
        <Field label="操作人 *">
          <input
            value={operator}
            onChange={(event) => setOperator(event.target.value)}
            placeholder="如：项目管理办公室"
          />
        </Field>
        {isCompletion ? (
          <Field label="完工验收结论">
            <select value={conclusion} onChange={(event) => setConclusion(event.target.value)}>
              {(dictionaries?.milestone_conclusion || [])
                .filter((item) => item !== '未通过')
                .map((item) => (
                  <option key={item}>{item}</option>
                ))}
            </select>
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
