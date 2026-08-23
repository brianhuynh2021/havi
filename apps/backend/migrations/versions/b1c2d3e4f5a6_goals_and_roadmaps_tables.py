"""goals and roadmaps tables (Havi 3.0)

Revision ID: b1c2d3e4f5a6
Revises: a7b8c9d0e1f2
Create Date: 2026-08-23 22:56:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b1c2d3e4f5a6'
down_revision: Union[str, Sequence[str], None] = 'a7b8c9d0e1f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. goals table
    op.create_table(
        'goals',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('workspace_id', sa.Uuid(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('evidence_definition', sa.Text(), nullable=False),
        sa.Column('target_deadline', sa.DateTime(timezone=True), nullable=True),
        sa.Column('weekly_capacity_hours', sa.Integer(), nullable=False),
        sa.Column('constraints', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_goals_workspace_id'), 'goals', ['workspace_id'], unique=False)
    op.create_index(op.f('ix_goals_status'), 'goals', ['status'], unique=False)

    # 2. roadmaps table
    op.create_table(
        'roadmaps',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('workspace_id', sa.Uuid(), nullable=False),
        sa.Column('goal_id', sa.Uuid(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('horizon_90d', sa.Text(), nullable=False),
        sa.Column('horizon_30d', sa.Text(), nullable=False),
        sa.Column('horizon_7d', sa.Text(), nullable=False),
        sa.Column('assumptions', sa.JSON(), nullable=True),
        sa.Column('confidence_score', sa.Float(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['goal_id'], ['goals.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_roadmaps_workspace_id'), 'roadmaps', ['workspace_id'], unique=False)
    op.create_index(op.f('ix_roadmaps_goal_id'), 'roadmaps', ['goal_id'], unique=False)
    op.create_index(op.f('ix_roadmaps_status'), 'roadmaps', ['status'], unique=False)

    # 3. roadmap_tasks table
    op.create_table(
        'roadmap_tasks',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('workspace_id', sa.Uuid(), nullable=False),
        sa.Column('roadmap_id', sa.Uuid(), nullable=False),
        sa.Column('goal_id', sa.Uuid(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('why_this_is_next', sa.Text(), nullable=False),
        sa.Column('time_estimate_minutes', sa.Integer(), nullable=False),
        sa.Column('owner_type', sa.String(length=20), nullable=False),
        sa.Column('capability_module', sa.String(length=50), nullable=False),
        sa.Column('inputs_needed', sa.Text(), nullable=True),
        sa.Column('done_rule', sa.Text(), nullable=False),
        sa.Column('fallback_action', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('scheduled_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('evidence_notes', sa.Text(), nullable=True),
        sa.Column('order_index', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['goal_id'], ['goals.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['roadmap_id'], ['roadmaps.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_roadmap_tasks_workspace_id'), 'roadmap_tasks', ['workspace_id'], unique=False)
    op.create_index(op.f('ix_roadmap_tasks_roadmap_id'), 'roadmap_tasks', ['roadmap_id'], unique=False)
    op.create_index(op.f('ix_roadmap_tasks_goal_id'), 'roadmap_tasks', ['goal_id'], unique=False)
    op.create_index(op.f('ix_roadmap_tasks_status'), 'roadmap_tasks', ['status'], unique=False)
    op.create_index(op.f('ix_roadmap_tasks_scheduled_date'), 'roadmap_tasks', ['scheduled_date'], unique=False)

    # 4. evidence_logs table
    op.create_table(
        'evidence_logs',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('workspace_id', sa.Uuid(), nullable=False),
        sa.Column('goal_id', sa.Uuid(), nullable=False),
        sa.Column('task_id', sa.Uuid(), nullable=True),
        sa.Column('source', sa.String(length=50), nullable=False),
        sa.Column('evidence_type', sa.String(length=50), nullable=False),
        sa.Column('value_number', sa.Float(), nullable=True),
        sa.Column('value_text', sa.Text(), nullable=False),
        sa.Column('media_asset_id', sa.Uuid(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['goal_id'], ['goals.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['media_asset_id'], ['media_assets.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['task_id'], ['roadmap_tasks.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_evidence_logs_workspace_id'), 'evidence_logs', ['workspace_id'], unique=False)
    op.create_index(op.f('ix_evidence_logs_goal_id'), 'evidence_logs', ['goal_id'], unique=False)
    op.create_index(op.f('ix_evidence_logs_task_id'), 'evidence_logs', ['task_id'], unique=False)

    # 5. roadmap_reviews table
    op.create_table(
        'roadmap_reviews',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('workspace_id', sa.Uuid(), nullable=False),
        sa.Column('goal_id', sa.Uuid(), nullable=False),
        sa.Column('roadmap_id', sa.Uuid(), nullable=False),
        sa.Column('review_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_summary', sa.Text(), nullable=False),
        sa.Column('evidence_summary', sa.Text(), nullable=False),
        sa.Column('obstacles_summary', sa.Text(), nullable=False),
        sa.Column('decision', sa.String(length=20), nullable=False),
        sa.Column('replan_diff', sa.JSON(), nullable=True),
        sa.Column('user_accepted', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['goal_id'], ['goals.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['roadmap_id'], ['roadmaps.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_roadmap_reviews_workspace_id'), 'roadmap_reviews', ['workspace_id'], unique=False)
    op.create_index(op.f('ix_roadmap_reviews_goal_id'), 'roadmap_reviews', ['goal_id'], unique=False)
    op.create_index(op.f('ix_roadmap_reviews_roadmap_id'), 'roadmap_reviews', ['roadmap_id'], unique=False)


def downgrade() -> None:
    op.drop_table('roadmap_reviews')
    op.drop_table('evidence_logs')
    op.drop_table('roadmap_tasks')
    op.drop_table('roadmaps')
    op.drop_table('goals')
