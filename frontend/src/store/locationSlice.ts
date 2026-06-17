import { createSlice, createAsyncThunk, PayloadAction } from "@reduxjs/toolkit";
import { api } from "../services/api";

interface Location {
  id: number;
  address: string;
  name: string | null;
  status: string;
  area_sqm: number | null;
  created_at: string;
  total_score?: number | null;
}

interface LocationState {
  items: Location[];
  total: number;
  page: number;
  loading: boolean;
  error: string | null;
}

const initialState: LocationState = {
  items: [],
  total: 0,
  page: 1,
  loading: false,
  error: null,
};

export const fetchLocations = createAsyncThunk(
  "locations/fetchAll",
  async ({ page = 1, status }: { page?: number; status?: string } = {}) => {
    const params: Record<string, any> = { page, page_size: 20 };
    if (status) params.status = status;
    const { data } = await api.get("/locations", { params });
    return data;
  }
);

export const deleteLocation = createAsyncThunk(
  "locations/delete",
  async (id: number) => {
    await api.delete(`/locations/${id}`);
    return id;
  }
);

const locationSlice = createSlice({
  name: "locations",
  initialState,
  reducers: {
    setPage(state, action: PayloadAction<number>) {
      state.page = action.payload;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchLocations.pending, (state) => { state.loading = true; })
      .addCase(fetchLocations.fulfilled, (state, action) => {
        state.loading = false;
        state.items = action.payload.items;
        state.total = action.payload.total;
      })
      .addCase(fetchLocations.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || "Failed to load locations";
      })
      .addCase(deleteLocation.fulfilled, (state, action) => {
        state.items = state.items.filter((l) => l.id !== action.payload);
        state.total -= 1;
      });
  },
});

export const { setPage } = locationSlice.actions;
export default locationSlice.reducer;
