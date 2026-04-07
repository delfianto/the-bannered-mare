import type { components } from "@/api/schema";
import { allModelFamiliesMock } from "@/mocks/data/model-families-data";

type ModelFamilyPage = components["schemas"]["PaginatedResponse_ModelFamilyListResponse_"];
type ModelFamilyItem = components["schemas"]["ModelFamilyListResponse"];

// Helper to strip 'parameters' for the list view to reduce payload size
const toSummary = (item: any): ModelFamilyItem => {
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const { parameters, ...rest } = item;
  return rest as ModelFamilyItem;
};

// Helper to generate a paginated response structure
const createPage = (
  items: any[],
  page: number,
  totalItems: number,
  limit: number = 10,
): ModelFamilyPage => {
  const totalPages = Math.ceil(totalItems / limit);

  return {
    items: items.map(toSummary),
    meta: {
      total: totalItems,
      page: page,
      limit: limit,
      has_more: page < totalPages,
    },
  };
};

const PAGE_LIMIT = 10;
const totalCount = allModelFamiliesMock.length;
const totalPages = Math.ceil(totalCount / PAGE_LIMIT);

// Generate pages dynamically (19 families = 2 pages: 10 + 9)
export const modelFamiliesPages: ModelFamilyPage[] = Array.from(
  { length: totalPages },
  (_, i) => {
    const pageNum = i + 1;
    const start = i * PAGE_LIMIT;
    const end = start + PAGE_LIMIT;
    return createPage(allModelFamiliesMock.slice(start, end), pageNum, totalCount, PAGE_LIMIT);
  },
);

// Generate the filtered "Claude" result dynamically
const claudeItems = allModelFamiliesMock.filter((item) =>
  item.name.toLowerCase().includes("claude"),
);

export const modelFamiliesFilteredByName: ModelFamilyPage = createPage(
  claudeItems,
  1,
  claudeItems.length,
  PAGE_LIMIT,
);
