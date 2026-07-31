CREATE SEQUENCE agent_resource_id_seq START WITH 10000;

CREATE TABLE resource (
  id BIGINT PRIMARY KEY,
  type VARCHAR(16) NOT NULL,
  name VARCHAR(80) NOT NULL,
  normalized_name VARCHAR(160) NOT NULL,
  description VARCHAR(500),
  current_version_id BIGINT,
  archived BOOLEAN NOT NULL DEFAULT FALSE,
  environment JSON,
  create_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
  update_at TIMESTAMP WITH TIME ZONE,
  CONSTRAINT ck_resource_type CHECK (type IN ('scenario', 'strategy', 'agent', 'environment')),
  CONSTRAINT uq_resource_type_normalized_name UNIQUE (type, normalized_name)
);

CREATE TABLE resource_version (
  id BIGINT PRIMARY KEY,
  resource_id BIGINT NOT NULL REFERENCES resource(id) ON DELETE CASCADE,
  version VARCHAR(32) NOT NULL,
  revision_number INTEGER,
  package_version VARCHAR(64),
  format VARCHAR(16) NOT NULL,
  file_name VARCHAR(255),
  size BIGINT,
  checksum VARCHAR(64),
  object_key VARCHAR(512),
  parsed_data JSON,
  validation JSON NOT NULL,
  create_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
  update_at TIMESTAMP WITH TIME ZONE,
  CONSTRAINT uq_resource_version_name UNIQUE (resource_id, version),
  CONSTRAINT uq_resource_revision_number UNIQUE (resource_id, revision_number)
);

CREATE TABLE branch_scheme (
  id BIGINT PRIMARY KEY,
  normalized_name VARCHAR(160) NOT NULL UNIQUE,
  head_revision_id BIGINT NOT NULL,
  head_revision_number INTEGER NOT NULL,
  published_revision_id BIGINT,
  published_revision_number INTEGER,
  created_by VARCHAR(80) NOT NULL,
  create_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
  update_at TIMESTAMP WITH TIME ZONE
);

CREATE TABLE branch_scheme_revision (
  id BIGINT PRIMARY KEY,
  branch_scheme_id BIGINT NOT NULL REFERENCES branch_scheme(id) ON DELETE CASCADE,
  revision_number INTEGER NOT NULL,
  parent_revision_id BIGINT,
  name VARCHAR(80) NOT NULL,
  description VARCHAR(500) NOT NULL,
  scenario_type_key VARCHAR(128) NOT NULL,
  side_key VARCHAR(64) NOT NULL,
  status VARCHAR(16) NOT NULL,
  graph JSON NOT NULL,
  origin JSON,
  created_by VARCHAR(80) NOT NULL,
  create_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
  update_at TIMESTAMP WITH TIME ZONE,
  CONSTRAINT ck_branch_scheme_revision_status CHECK (status IN ('draft', 'configured')),
  CONSTRAINT uq_branch_scheme_revision_number UNIQUE (branch_scheme_id, revision_number)
);

CREATE TABLE deduction (
  id BIGINT PRIMARY KEY,
  name VARCHAR(80) NOT NULL,
  normalized_name VARCHAR(160) NOT NULL UNIQUE,
  description VARCHAR(500) NOT NULL DEFAULT '',
  scenario_type_key VARCHAR(128) NOT NULL,
  status VARCHAR(16) NOT NULL DEFAULT 'draft',
  graph JSON NOT NULL,
  created_by VARCHAR(80) NOT NULL DEFAULT '当前用户',
  create_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
  update_at TIMESTAMP WITH TIME ZONE,
  CONSTRAINT ck_deduction_status CHECK (status IN ('draft', 'ready'))
);

CREATE TABLE deduction_run (
  id BIGINT PRIMARY KEY,
  deduction_id BIGINT NOT NULL REFERENCES deduction(id) ON DELETE CASCADE,
  status VARCHAR(16) NOT NULL,
  environment_resource_id BIGINT NOT NULL,
  environment_name VARCHAR(80) NOT NULL,
  environment_snapshot JSON NOT NULL,
  environment_runtime JSON NOT NULL,
  branches JSON NOT NULL,
  engine_request JSON NOT NULL,
  sim_time VARCHAR(64) NOT NULL,
  started_at TIMESTAMP WITH TIME ZONE NOT NULL,
  sequence BIGINT NOT NULL DEFAULT 0,
  engine_cursor BIGINT NOT NULL DEFAULT 0,
  failure_reason VARCHAR(500),
  ended_at TIMESTAMP WITH TIME ZONE,
  create_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
  update_at TIMESTAMP WITH TIME ZONE,
  CONSTRAINT ck_deduction_run_status CHECK (
    status IN ('starting', 'running', 'stopping', 'finished', 'failed', 'stopped')
  )
);

CREATE UNIQUE INDEX uq_deduction_run_active ON deduction_run(deduction_id)
WHERE status IN ('starting', 'running', 'stopping');

CREATE TABLE deduction_task (
  id BIGINT PRIMARY KEY,
  run_id BIGINT NOT NULL REFERENCES deduction_run(id) ON DELETE CASCADE,
  kind VARCHAR(16) NOT NULL,
  branch_node_id VARCHAR(128) NOT NULL,
  branch_scheme_id BIGINT NOT NULL,
  branch_scheme_name VARCHAR(80) NOT NULL,
  name VARCHAR(80) NOT NULL,
  dependency_ids JSON NOT NULL,
  status VARCHAR(16) NOT NULL,
  parent_task_id BIGINT,
  source_node_id VARCHAR(128),
  agent_resource_id BIGINT,
  agent_version_id BIGINT,
  agent_revision_number INTEGER,
  agent_checksum VARCHAR(64),
  agent_name VARCHAR(80),
  agent_parameters JSON,
  started_at TIMESTAMP WITH TIME ZONE,
  ended_at TIMESTAMP WITH TIME ZONE,
  create_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
  update_at TIMESTAMP WITH TIME ZONE,
  CONSTRAINT ck_deduction_task_kind CHECK (kind IN ('container', 'agent')),
  CONSTRAINT ck_deduction_task_status CHECK (
    status IN ('READY', 'PENDING', 'RUNNING', 'STOPPING', 'END', 'ERROR')
  )
);

CREATE TABLE deduction_runtime_message (
  id BIGINT PRIMARY KEY,
  run_id BIGINT NOT NULL REFERENCES deduction_run(id) ON DELETE CASCADE,
  sequence BIGINT NOT NULL,
  type VARCHAR(16) NOT NULL,
  payload JSON NOT NULL,
  emitted_at TIMESTAMP WITH TIME ZONE NOT NULL,
  task_id BIGINT,
  branch_node_id VARCHAR(128),
  create_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
  update_at TIMESTAMP WITH TIME ZONE,
  CONSTRAINT uq_runtime_message_sequence UNIQUE (run_id, sequence)
);

CREATE INDEX ix_resource_type ON resource(type);
CREATE INDEX ix_resource_archived ON resource(archived);
CREATE INDEX ix_resource_version_resource_id ON resource_version(resource_id);
CREATE INDEX ix_resource_version_checksum ON resource_version(checksum);
CREATE INDEX ix_branch_scheme_revision_branch_scheme_id ON branch_scheme_revision(branch_scheme_id);
CREATE INDEX ix_deduction_status ON deduction(status);
CREATE INDEX ix_deduction_run_deduction_id ON deduction_run(deduction_id);
CREATE INDEX ix_deduction_run_status ON deduction_run(status);
CREATE INDEX ix_deduction_task_run_id ON deduction_task(run_id);
CREATE INDEX ix_runtime_message_run_type_sequence
  ON deduction_runtime_message(run_id, type, sequence);
CREATE INDEX ix_runtime_message_run_task_sequence
  ON deduction_runtime_message(run_id, task_id, sequence);

COMMENT ON TABLE resource IS '四类资源聚合；智能体删除为归档。';
COMMENT ON TABLE resource_version IS '不可变资源版本；智能体使用 R1/R2 平台修订。';
COMMENT ON COLUMN resource_version.package_version IS '智能体 ZIP config.yaml VERSION，与平台修订号相互独立。';
COMMENT ON TABLE branch_scheme IS '分支方案聚合及 head/published 修订指针。';
COMMENT ON TABLE branch_scheme_revision IS '不可变分支方案修订。';
COMMENT ON TABLE deduction IS '推演定义，仅持久化 draft/ready；graph 固定引用具体分支方案修订。';
COMMENT ON TABLE deduction_run IS '推演的一次运行及其固定输入快照。';
COMMENT ON TABLE deduction_task IS '与 Matrix Task ID 一一对应的运行任务。';
COMMENT ON TABLE deduction_runtime_message IS '支持 Snapshot、历史查询与 SSE 回放的运行消息。';
