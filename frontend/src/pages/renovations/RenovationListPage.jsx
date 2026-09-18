import { useState } from 'react';
import { Link } from 'react-router-dom';

import { renovationApi } from '../../api/renovations.js';
import { restroomApi } from '../../api/restrooms.js';
import DataTable from '../../components/DataTable.jsx';
import Field from '../../components/Field.jsx';
import PageHeader from '../../components/PageHeader.jsx';
import Pagination from '../../components/Pagination.jsx';
import { StatusTag } from '../../components/Tags.jsx';
import { useAsync } from '../../hooks/useAsync.js';
import { useDictionaries } from '../../hooks/useDictionaries.js';
import { useListQuery } from '../../hooks/useListQuery.js';
import { formatDate } from '../../utils/format.js';
import ProgressBar from './ProgressBar.jsx';
import RenovationFormModal from './RenovationFormModal.jsx';

const DEFAULT_FILTERS = {
  keyword: '',
  district: '',
  status: '',
};

export default function RenovationListPage() {
  const { dictionaries } = useDictionaries();
  const [showForm, setShowForm] = useState(false);

  const list = useListQuery((params) => renovationApi.list(params), DEFAULT_FILTERS, 10);
  const { data: districts } = useAsync(() => restroomApi.districts(), []);

  return (
    <>
      <PageHeader
        title="公厕改造项目"
        description="立项登记、节点进度与阶段验收、完工归档全流程跟踪，改造期间公厕自动停用"
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
                placeholder="项目名称 / 编号 / 施工单位"
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
                key: 'title',
                title: '项目名称',
                wrap: true,
                render: (row) => <Link to={`/renovations/${row.id}`}>{row.title}</Link>,
              },
              {
                key: 'restroom',
                title: '所属公厕',
                render: (row) =>
                  row.restroom ? (
                    <Link to={`/restrooms/${row.restroom.id}`}>{row.restroom.name}</Link>
                  ) : (
                    '-'
                  ),
              },
              { key: 'contractor', title: '施工单位', wrap: true },
              {
                key: 'planned',
                title: '计划工期',
                render: (row) => `${formatDate(row.planned_start)} ~ ${formatDate(row.planned_end)}`,
              },
              {
                key: 'budget',
                title: '预算',
                render: (row) => `${row.budget} 万元`,
              },
              {
                key: 'progress',
                title: '进度',
                render: (row) => <ProgressBar value={row.progress} />,
              },
              {
                key: 'status',
                title: '状态',
                render: (row) => (
                  <span className="inline">
                    <StatusTag status={row.status} />
                    {row.schedule_overdue ? <span className="tag tag-danger">工期超期</span> : null}
                  </span>
                ),
              },
              {
                key: 'actions',
                title: '操作',
                render: (row) => (
                  <Link className="btn-link" to={`/renovations/${row.id}`}>
                    详情 / 推进
                  </Link>
                ),
              },
            ]}
          />
          <Pagination meta={list.meta} onPageChange={list.setPage} />
        </section>
      </div>

      {showForm ? (
        <RenovationFormModal onClose={() => setShowForm(false)} onSaved={list.reload} />
      ) : null}
    </>
  );
}
