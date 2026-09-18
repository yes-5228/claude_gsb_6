import { useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';

import { projectApi } from '../../api/projects.js';
import DataTable from '../../components/DataTable.jsx';
import DetailList from '../../components/DetailList.jsx';
import PageHeader from '../../components/PageHeader.jsx';
import { AcceptanceTag, StatusTag } from '../../components/Tags.jsx';
import Timeline from '../../components/Timeline.jsx';
import { useToast } from '../../components/Toast.jsx';
import { useAsync } from '../../hooks/useAsync.js';
import { formatDate, formatDateTime } from '../../utils/format.js';
import NodeFormModal from './NodeFormModal.jsx';
import ProjectActionModal from './ProjectActionModal.jsx';

export default function ProjectDetailPage() {
  const { projectId } = useParams();
  const navigate = useNavigate();
  const toast = useToast();
  const [activeOption, setActiveOption] = useState(null);
  const [nodeModal, setNodeModal] = useState(null); // { mode, node? }
  const [saving, setSaving] = useState(false);

  const { data: project, loading, error, reload } = useAsync(
    () => projectApi.detail(projectId),
    [projectId],
  );
  const { data: options } = useAsync(() => projectApi.transitions(projectId), [projectId]);

  const sealed = project?.status === '已验收';
  const processing = project?.status === '施工中';
  const canAcceptNode = project && ['施工中', '待验收'].includes(project.status);

  const submitTransition = async (payload) => {
    setSaving(true);
    try {
      await projectApi.changeStatus(projectId, payload);
      toast.success(payload.to_status === '已验收' ? '竣工验收通过，公厕已恢复开放' : '项目状态已更新');
      setActiveOption(null);
      reload();
    } catch (err) {
      toast.error(err.message);
    } finally {
      setSaving(false);
    }
  };

  const submitNode = async (payload) => {
    setSaving(true);
    try {
      if (nodeModal.mode === 'create') {
        await projectApi.addNode(projectId, payload);
        toast.success('进度节点已登记');
      } else {
        await projectApi.acceptNode(projectId, nodeModal.node.id, payload);
        toast.success('阶段验收结论已登记');
      }
      setNodeModal(null);
      reload();
    } catch (err) {
      toast.error(err.message);
    } finally {
      setSaving(false);
    }
  };

  const removeNode = async (node) => {
    if (!window.confirm(`确认删除节点「${node.title}」？`)) return;
    try {
      await projectApi.removeNode(projectId, node.id);
      toast.success('节点已删除');
      reload();
    } catch (err) {
      toast.error(err.message);
    }
  };

  const remove = async () => {
    if (
      !window.confirm(
        `确认删除项目「${project.code}」？删除后公厕将恢复为「${project.previous_restroom_status}」状态。`,
      )
    )
      return;
    try {
      await projectApi.remove(projectId);
      toast.success('项目已删除，公厕状态已恢复');
      navigate('/projects');
    } catch (err) {
      toast.error(err.message);
    }
  };

  return (
    <>
      <PageHeader
        title={project ? `改造项目 ${project.code}` : '改造项目详情'}
        description={project ? `${project.restroom?.name} · ${project.construction_unit}` : '加载中…'}
        actions={
          <>
            <Link className="btn" to="/projects">
              返回列表
            </Link>
            {!sealed ? (
              <button type="button" className="btn btn-danger" onClick={remove}>
                删除项目
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
                  <h3>项目档案</h3>
                  <StatusTag status={project.status} />
                  {project.is_delayed ? <span className="tag tag-danger">工期超期</span> : null}
                  {sealed ? <span className="tag tag-neutral">档案已封存</span> : null}
                </div>
                <span className="hint">立项时间：{formatDateTime(project.setup_time)}</span>
              </div>
              <DetailList
                items={[
                  {
                    label: '改造公厕',
                    value: project.restroom ? (
                      <Link to={`/restrooms/${project.restroom.id}`}>
                        {project.restroom.name}（{project.restroom.district}）
                      </Link>
                    ) : (
                      '-'
                    ),
                  },
                  { label: '改造事由', value: project.reason },
                  { label: '施工单位', value: project.construction_unit || '-' },
                  { label: '现场负责人', value: project.project_manager || '-' },
                  { label: '联系电话', value: project.contact_phone || '-' },
                  {
                    label: '计划工期',
                    value: project.planned_start_date ? (
                      <span>
                        {formatDate(project.planned_start_date)} ~ {formatDate(project.planned_end_date)}
                        （{project.plan_duration_days} 天）
                      </span>
                    ) : (
                      '-'
                    ),
                  },
                  {
                    label: '预算金额',
                    value: `${Number(project.budget).toFixed(1)} 万元`,
                  },
                  {
                    label: '实际开工 / 结算造价',
                    value: `${formatDateTime(project.actual_start_time)} / ${
                      project.actual_cost != null ? `${Number(project.actual_cost).toFixed(1)} 万元` : '-'
                    }`,
                  },
                  {
                    label: '立项前公厕状态',
                    value: project.previous_restroom_status || '-',
                  },
                  {
                    label: '竣工验收',
                    value: sealed ? (
                      <span>
                        {formatDateTime(project.accepted_at)} · {project.accepted_opinion}
                      </span>
                    ) : (
                      '未验收'
                    ),
                  },
                  { label: '备注', value: project.remark || '无' },
                ]}
              />
            </section>

            <section className="card">
              <div className="card-title">
                <h3>项目流转</h3>
                <span className="hint">按流程推进，越级操作会被服务端拒绝</span>
              </div>
              {sealed ? (
                <div className="alert alert-info">该项目已竣工验收，公厕已恢复开放，项目档案只读封存。</div>
              ) : (
                <div className="action-group">
                  {(options || []).map((option) => (
                    <button
                      key={option.status}
                      type="button"
                      className={`btn${option.status === '已验收' ? ' btn-primary' : ''}`}
                      onClick={() => setActiveOption(option)}
                    >
                      {option.action}（变更为「{option.status}」）
                    </button>
                  ))}
                </div>
              )}
            </section>

            <section className="card">
              <div className="card-title">
                <h3>进度节点与阶段验收</h3>
                {processing ? (
                  <button type="button" className="btn btn-sm btn-primary" onClick={() => setNodeModal({ mode: 'create' })}>
                    + 登记进度节点
                  </button>
                ) : (
                  <span className="hint">
                    {sealed ? '档案已封存' : '仅「施工中」可登记节点'}
                  </span>
                )}
              </div>
              <DataTable
                rows={project.nodes}
                emptyText="暂无进度节点"
                columns={[
                  { key: 'node_date', title: '节点日期', render: (row) => formatDate(row.node_date) },
                  { key: 'title', title: '节点名称' },
                  {
                    key: 'progress_percent',
                    title: '完成度',
                    render: (row) =>
                      row.progress_percent != null ? `${row.progress_percent}%` : '-',
                  },
                  { key: 'progress', title: '进度说明', wrap: true, render: (row) => row.progress || '-' },
                  {
                    key: 'acceptance',
                    title: '阶段验收',
                    render: (row) => (
                      <div className="inline">
                        <AcceptanceTag result={row.acceptance_result} />
                        {row.acceptance_result ? (
                          <span className="hint">
                            {row.acceptor} · {formatDateTime(row.accepted_at)}
                          </span>
                        ) : null}
                      </div>
                    ),
                  },
                  {
                    key: 'acceptance_opinion',
                    title: '验收意见',
                    wrap: true,
                    render: (row) => row.acceptance_opinion || '-',
                  },
                  {
                    key: 'actions',
                    title: '操作',
                    render: (row) =>
                      sealed ? (
                        <span className="hint">-</span>
                      ) : (
                        <div className="inline">
                          {canAcceptNode ? (
                            <button
                              type="button"
                              className="btn-link"
                              onClick={() => setNodeModal({ mode: 'accept', node: row })}
                            >
                              {row.acceptance_result ? '复验' : '阶段验收'}
                            </button>
                          ) : null}
                          {processing ? (
                            <button
                              type="button"
                              className="btn-link danger"
                              onClick={() => removeNode(row)}
                            >
                              删除
                            </button>
                          ) : null}
                        </div>
                      ),
                  },
                ]}
              />
            </section>

            <section className="card">
              <div className="card-title">
                <h3>项目流转轨迹</h3>
                <span className="hint">共 {project.records.length} 条记录</span>
              </div>
              <Timeline records={project.records} />
            </section>
          </>
        ) : null}
      </div>

      {activeOption && project ? (
        <ProjectActionModal
          option={activeOption}
          project={project}
          saving={saving}
          onClose={() => setActiveOption(null)}
          onSubmit={submitTransition}
        />
      ) : null}

      {nodeModal && project ? (
        <NodeFormModal
          mode={nodeModal.mode}
          node={nodeModal.node}
          project={project}
          saving={saving}
          onClose={() => setNodeModal(null)}
          onSubmit={submitNode}
        />
      ) : null}
    </>
  );
}
