import { useState } from 'react';
import { Link } from 'react-router-dom';

import { projectApi } from '../../api/projects.js';
import { restroomApi } from '../../api/restrooms.js';
import DataTable from '../../components/DataTable.jsx';
import Field from '../../components/Field.jsx';
import PageHeader from '../../components/PageHeader.jsx';
import Pagination from '../../components/Pagination.jsx';
import { StatusTag } from '../../components/Tags.jsx';
import { useToast } from '../../components/Toast.jsx';
import { useAsync } from '../../hooks/useAsync.js';
import { useDictionaries } from '../../hooks/useDictionaries.js';
import { useListQuery } from '../../hooks/useListQuery.js';
import { formatDate, formatDateTime } from '../../utils/format.js';
import ProjectFormModal from './ProjectFormModal.jsx';

const DEFAULT_FILTERS = {
  keyword: '',
  district: '',
  status: '',
  open_only: '',
  delayed: '',
};

export default function ProjectListPage() {
  const { dictionaries } = useDictionaries();
  const toast = useToast();
  const [showForm, setShowForm] = useState(false);

  const list = useListQuery((params) => projectApi.list(params), DEFAULT_FILTERS, 10);
  const { data: districts } = useAsync(() => restroomApi.districts(), []);

  const remove = async (row) => {
    if (
      !window.confirm(
        `确认删除改造项目「${row.code}」？删除后公厕将恢复为「${row.previous_restroom_status}」状态。`,
      )
    )
      return;
    try {
      await projectApi.remove(row.id);
      toast.success('项目已删除，公厕状态已恢复');
      list.reload();
    } catch (err) {
      toast.error(err.message);
    }
  };

  return (
    <>
      <PageHeader
        title="公厕改造项目跟踪"
        description="立项登记、节点进度与阶段验收全流程跟踪；立项即停用，验收后自动恢复"
        actions={
          <button type="button" className="btn btn-primary" onClick={() => setShowForm(true)}>
            + 立项登记
          </button>
        }
      />
      <div className="content">
        <section className="card">
          <div className="filter-bar">
            <Field label="关键字" full>
              <input
                value={list.filters.keyword}
                placeholder="改造事由 / 编号 / 施工单位 / 负责人"
                onChange={(event) => list.updateFilter('keyword', event.target.value)}
              />
            </Field>
            <Field label="项目状态">
              <select
                value={list.filters.status}
                onChange={(event) => list.updateFilter('status', event.target.value)}
              >
                <option value="">全部</option>
                {(dictionaries?.renovation_status || []).map((item) => (
                  <option key={item}>{item}</option>
                ))}
              </select>
            </Field>
            <Field label="所属区域">
              <select
                value={list.filters.district}
                onChange={(event) => list.updateFilter('district', event.target.value)}
              >
                <option value="">全部</option>
                {(districts || []).map((item) => (
                  <option key={item}>{item}</option>
                ))}
              </select>
            </Field>
            <Field label="工期情况">
              <select
                value={list.filters.delayed}
                onChange={(event) => list.updateFilter('delayed', event.target.value)}
              >
                <option value="">全部</option>
                <option value="true">仅看工期超期</option>
              </select>
            </Field>
            <Field label="进行情况">
              <select
                value={list.filters.open_only}
                onChange={(event) => list.updateFilter('open_only', event.target.value)}
              >
                <option value="">全部</option>
                <option value="true">仅看进行中</option>
              </select>
            </Field>
            <button type="button" className="btn" onClick={list.resetFilters}>
              重置
            </button>
          </div>
        </section>

        <section className="card">
          <DataTable
            loading={list.loading}
            error={list.error}
            rows={list.items}
            emptyText="暂无改造项目"
            columns={[
              { key: 'code', title: '项目编号' },
              {
                key: 'reason',
                title: '改造事由',
                wrap: true,
                render: (row) => <Link to={`/projects/${row.id}`}>{row.reason}</Link>,
              },
              {
                key: 'restroom',
                title: '改造公厕',
                render: (row) =>
                  row.restroom ? (
                    <Link to={`/restrooms/${row.restroom.id}`}>{row.restroom.name}</Link>
                  ) : (
                    '-'
                  ),
              },
              { key: 'construction_unit', title: '施工单位' },
              {
                key: 'status',
                title: '状态',
                render: (row) => (
                  <span className="inline">
                    <StatusTag status={row.status} />
                    {row.is_delayed ? <span className="tag tag-danger">工期超期</span> : null}
                  </span>
                ),
              },
              {
                key: 'budget',
                title: '预算(万元)',
                render: (row) => `${Number(row.budget).toFixed(1)}`,
              },
              {
                key: 'plan',
                title: '计划工期',
                render: (row) =>
                  row.planned_start_date ? (
                    <span>
                      {formatDate(row.planned_start_date)} ~ {formatDate(row.planned_end_date)}
                      {row.plan_duration_days ? `（${row.plan_duration_days} 天）` : ''}
                    </span>
                  ) : (
                    '-'
                  ),
              },
              {
                key: 'setup_time',
                title: '立项时间',
                render: (row) => formatDateTime(row.setup_time),
              },
              {
                key: 'actions',
                title: '操作',
                render: (row) => (
                  <div className="inline">
                    <Link className="btn-link" to={`/projects/${row.id}`}>
                      详情 / 跟踪
                    </Link>
                    {row.status !== '已验收' ? (
                      <button type="button" className="btn-link danger" onClick={() => remove(row)}>
                        删除
                      </button>
                    ) : (
                      <span className="hint">已封存</span>
                    )}
                  </div>
                ),
              },
            ]}
          />
          <Pagination meta={list.meta} onPageChange={list.setPage} />
        </section>
      </div>

      {showForm ? <ProjectFormModal onClose={() => setShowForm(false)} onSaved={list.reload} /> : null}
    </>
  );
}
