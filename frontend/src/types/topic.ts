export interface TopicOut {
  id: number;
  college_id: number;
  name: string;
  slug: string;
  parent_id: number | null;
  order_index: number | null;
}

export interface TopicCreate {
  name: string;
  slug: string;
  parent_id?: number | null;
  order_index?: number | null;
}

export type TopicUpdate = Partial<TopicCreate>;

export interface TopicTree extends TopicOut {
  children: TopicTree[];
}
