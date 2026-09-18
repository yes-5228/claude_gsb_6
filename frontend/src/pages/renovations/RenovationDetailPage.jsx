import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';

import { renovationApi } from '../../api/renovations.js';
import DetailList from '../../components/DetailList.jsx';
import Field from '../../components/Field.jsx';
import PageHeader from '../../components/PageHeader.jsx';
import { StatusTag } from '../../components/Tags.jsx';
import { useToast } from '../../components/Toast.jsx';
import { useAsync } from '../../hooks/useAsync.js';
import { useDictionaries } from '../../hooks/useDictionaries.js';
import { formatDate, formatDateTime } from '../../utils/format.js';
import ProgressBar from './ProgressBar.jsx';
import RenovationActionModal from './RenovationActionModal.jsx';
import RenovationEditModal from './RenovationEditModal.jsx';

const EMPTY_MILESTONE = { node: '拆除清运', progress: 10, conclusion: '通过', operator: '', note: '' };

export default function RenovationDetailPage() {
  const { projectId } = useParams();
  const { dictionaries } = useDictionaries();
  const toast = useToast();
  const [activeOption, setActiveOption] = useState(null);
  const [showEdit, setShowEdit] = useState(false);
  const [saving, setSaving] = useState(false);
  const [milestone, setMilestone] = useState(EMPTY_MILESTONE);
  const [milestoneError, setMilestoneError] = useState(null);

  const { data: project, loading, error, reload } = useAsync(
    () => renovationApi.detail(projectId),
    [projectId],
  );
  const { data: options, reload: reloadOptions } = useAsync(
    () => renovationApi.transitions(projectId),
    [projectId],
  );

  const refresh = () => {
    reload();
    reloadOptions();
  };

  const submitTransition = async (payload) => {
    setSaving(true);
    try {
      await renovationApi.changeStatus(projectId, payload);
      toast.success(
        payload.to_status === '改造中'
          ? '项目状态已更新，改造期间公厕已自动停用'
          : payload.to_status === '已完工'
            ? '完工验收通过，公厕已恢复开放'
            : '项目状态已更新',
      );
      setActiveOption(null);
      refresh();
    } catch (err) {
      toast.error(err.message);
    } finally {
      setSaving(false);
    }
  };

  const submitMilestone = async (event) => {
    event.preventDefault();
    if (!milestone.operator.trim()) {
      setMilestoneError('请填写记录人');
      return;
    }
    setMilestoneError(null);
    try {
      await renovationApi.addMilestone(projectId, {
        node: milestone.node,
        progress: Number(milestone.progress),
        conclusion: milestone.conclusion,
        operator: milestone.operator.trim(),
        note: milestone.note || null,
      });
      toast.success('节点进度已记录');
      setMilestone((prev) => ({ ...prev, note: '' }));
      reload();
    } catch (err) {
      setMilestoneError(err.message);
    }
  };

  const archived = project ? ['已完工', '已取消'].includes(project.status) : false;

  return (
    <>
      <PageHeader
        title={project ? `项目 ${project.code}` : '项目详情'}
        description={project?.title}
        actions={
          <>
            <Link className="btn" to="/renovations">
              返回列表
            </Link>
            {!archived && project ? (
              <button type="button" className="btn" onClick={() => setShowEdit(true)}>
                编辑信息
              </button>
            ) : null}
          </>
        }
      />
      <div className="content">
        {error ? <div className="alert alert-error">{error.message}</div> : null}
        {loading && !project ? <div className="loading-block">加载中...</div> : null}

        {project ? (
          <>
            <section className="card">
              <div className="card-title">
                <div className="inline">
                  <h3>{project.title}</h3>
                  <StatusTag status={project.status} />
                  {project.schedule_overdue ? <span className="tag tag-danger">工期超期</span> : null}
                </div>
                <span className="hint">最后更新：{formatDateTime(project.updated_at)}</span>
              </div>
              <div style={{ marginBottom: 14 }}>
                <ProgressBar value={project.progress} />
              </div>
              <DetailList
                items={[
                  {
                    label: '所属公厕',
                    value: project.restroom ? (
                      <Link to={`/restrooms/${project.restroom.id}`}>
                        {project.restroom.name}（{project.restroom.district}）
                      </Link>
                    ) : (
                      '-'
                    ),
                  },
                  { label: '改造事由', value: project.reason },
                  { label: '立项时间', value: formatDateTime(project.approved_at) },
                  { label: '施工单位', value: project.contractor },
                  {
                    label: '计划工期',
                    value: `${formatDate(project.planned_start)} ~ ${formatDate(project.planned_end)}`,
                  },
                  { label: '预算', value: `${project.budget} 万元` },
                  { label: '实际开工', value: formatDateTime(project.started_at) },
                  { label: '完工时间', value: formatDateTime(project.finished_at) },
                  {
                    label: '完工验收结论',
                    value: project.completion_conclusion ? (
                      <StatusTag status={project.completion_conclusion} />
                    ) : (
                      '-'
                    ),
                  },
                  { label: '备注', value: project.remark || '无' },
                ]}
              />
            </section>

            <section className="card">
              <div className="card-title">
                <h3>项目流转</h3>
                <span className="hint">开工自动停用公厕，完工验收后自动恢复开放</span>
              </div>
              {options?.length ? (
                <div className="action-group">
                  {options.map((option) => (
                    <button
                      key={option.status}
                      type="button"
                      className={`btn${option.status === '已完工' ? ' btn-primary' : ''}`}
                      onClick={() => setActiveOption(option)}
                    >
                      {option.action}（变更为「{option.status}」）
                    </button>
                  ))}
                </div>
              ) : (
                <div className="alert alert-info">
                  项目已{project.status}，档案已归档保留，可供随时查阅。
                </div>
              )}

              {project.status === '改造中' ? (
                <form className="form-grid" style={{ marginTop: 18 }} onSubmit={submitMilestone}>
                  <Field label="节点名称">
                    <select
                      value={milestone.node}
                      onChange={(event) =>
                        setMilestone((prev) => ({ ...prev, node: event.target.value }))
                      }
                    >
                      {(dictionaries?.renovation_node_names || []).map((item) => (
                        <option key={item}>{item}</option>
                      ))}
                    </select>
                  </Field>
                  <Field label="整体进度（%）">
                    <input
                      type="number"
                      min="0"
                      max="100"
                      value={milestone.progress}
                      onChange={(event) =>
                        setMilestone((prev) => ({ ...prev, progress: event.target.value }))
                      }
                    />
                  </Field>
                  <Field label="阶段验收结论">
                    <select
                      value={milestone.conclusion}
                      onChange={(event) =>
                        setMilestone((prev) => ({ ...prev, conclusion: event.target.value }))
                      }
                    >
                      {(dictionaries?.milestone_conclusion || []).map((item) => (
                        <option key={item}>{item}</option>
                      ))}
                    </select>
                  </Field>
                  <Field label="记录人 *">
                    <input
                      value={milestone.operator}
                      onChange={(event) =>
                        setMilestone((prev) => ({ ...prev, operator: event.target.value }))
                      }
                      placeholder="如：监理单位"
                    />
                  </Field>
                  <Field label="节点说明" full>
                    <textarea
                      rows="2"
                      value={milestone.note}
                      onChange={(event) =>
                        setMilestone((prev) => ({ ...prev, note: event.target.value }))
                      }
                    />
                  </Field>
                  {milestoneError ? (
                    <div className="alert alert-error full">{milestoneError}</div>
                  ) : null}
                  <div className="full">
                    <button type="submit" className="btn">
                      记录节点进度
                    </button>
                  </div>
                </form>
              ) : null}
            </section>

            <section className="card">
              <div className="card-title">
                <h3>项目档案</h3>
                <span className="hint">共 {project.milestones.length} 条记录，永久保留</span>
              </div>
              {project.milestones.length ? (
                <ol className="timeline">
                  {project.milestones.map((record) => (
                    <li key={record.id}>
                      <div className="head">
                        <strong>{record.node}</strong>
                        <span className={`tag ${record.kind === '流程事件' ? 'tag-info' : 'tag-primary'}`}>
                          {record.kind}
                        </span>
                        {record.conclusion ? <StatusTag status={record.conclusion} /> : null}
                        {record.progress != null ? (
                          <span className="muted">进度 {record.progress}%</span>
                        ) : null}
                        <span className="time">{formatDateTime(record.created_at)}</span>
                        <span className="muted">记录人：{record.operator || '系统'}</span>
                      </div>
                      {record.note ? <div className="remark">{record.note}</div> : null}
                    </li>
                  ))}
                </ol>
              ) : (
                <div className="empty-block">暂无档案记录</div>
              )}
            </section>
          </>
        ) : null}
      </div>

      {activeOption && project ? (
        <RenovationActionModal
          option={activeOption}
          project={project}
          saving={saving}
          onClose={() => setActiveOption(null)}
          onSubmit={submitTransition}
        />
      ) : null}

      {showEdit && project ? (
        <RenovationEditModal project={project} onClose={() => setShowEdit(false)} onSaved={reload} />
      ) : null}
    </>
  );
}
