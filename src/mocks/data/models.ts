import type { components } from "@/api/schema";
import { allModelsMock } from "@/mocks/data/models-data";

type ModelPage = components["schemas"]["PaginatedResponse_ModelListResponse_"];
type ModelItem = components["schemas"]["ModelListResponse"];

// Helper to generate a paginated response structure
const createPage = (
  items: any[],
  page: number,
  totalItems: number,
  limit: number = 10,
): ModelPage => {
  const totalPages = Math.ceil(totalItems / limit);

  return {
    items: items as ModelItem[],
    meta: {
      total: totalItems,
      page: page,
      limit: limit,
      has_more: page < totalPages,
    },
  };
};

const PAGE_LIMIT = 10;
const totalCount = allModelsMock.length;
const totalPages = Math.ceil(totalCount / PAGE_LIMIT);

// Generate pages dynamically (34 models = 4 pages: 10 + 10 + 10 + 4)
export const modelsPages: ModelPage[] = Array.from({ length: totalPages }, (_, i) => {
  const pageNum = i + 1;
  const start = i * PAGE_LIMIT;
  const end = start + PAGE_LIMIT;
  return createPage(allModelsMock.slice(start, end), pageNum, totalCount, PAGE_LIMIT);
});

// Generate the filtered "Claude" result dynamically
const claudeItems = allModelsMock.filter((item) => item.name.toLowerCase().includes("claude"));

export const modelsFilteredByName: ModelPage = createPage(
  claudeItems,
  1,
  claudeItems.length,
  PAGE_LIMIT,
);
