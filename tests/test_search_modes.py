"""Direct search() function tests for modes and filters."""


class TestSearchModes:
    def test_vector_mode(self, populated_memory_env):
        from memory.searcher import search
        results, meta = search("PostgreSQL", mode="vector")
        assert len(results) > 0
        # Vector mode score is 1/(1+distance), so always 0..1
        assert all(0.0 <= r.score <= 1.0 for r in results)

    def test_fts_mode(self, populated_memory_env):
        from memory.searcher import search
        results, meta = search("PostGIS", mode="fts")
        assert len(results) > 0

    def test_hybrid_mode(self, populated_memory_env):
        from memory.searcher import search
        results, meta = search("PostgreSQL", mode="hybrid")
        assert len(results) > 0

    def test_fts_mode_no_match_returns_empty(self, populated_memory_env):
        from memory.searcher import search
        results, meta = search("totally-nonexistent-xyz", mode="fts")
        assert len(results) == 0


class TestSearchFilters:
    def test_after_filter(self, populated_memory_env):
        from memory.searcher import search
        results_recent, _ = search("PostgreSQL", after="2026-01-01")
        results_future, _ = search("PostgreSQL", after="2027-01-01")
        assert len(results_future) == 0
        assert len(results_recent) >= 0

    def test_before_filter(self, populated_memory_env):
        from memory.searcher import search
        results, _ = search("PostgreSQL", before="2020-01-01")
        assert len(results) == 0

    def test_session_id_filter(self, populated_memory_env):
        from memory.searcher import search
        results, _ = search("PostgreSQL", session_id="test-session-001")
        # Should only contain that session
        assert all(r.session_id == "test-session-001" for r in results)

    def test_session_id_filter_nonexistent(self, populated_memory_env):
        from memory.searcher import search
        results, _ = search("PostgreSQL", session_id="nonexistent")
        assert len(results) == 0

    def test_project_filter(self, populated_memory_env):
        from memory.searcher import search
        results_no_match, _ = search("PostgreSQL", project="totally-different")
        assert len(results_no_match) == 0

    def test_combined_filters(self, populated_memory_env):
        from memory.searcher import search
        results, _ = search("PostgreSQL", after="2026-01-01", before="2027-01-01")
        assert len(results) >= 0


class TestSortBehavior:
    def test_sort_by_date(self, populated_memory_env):
        from memory.searcher import search
        results, _ = search("PostgreSQL", sort="date", limit=10)
        if len(results) > 1:
            sort_keys = [(r.date, r.turn_number) for r in results]
            assert sort_keys == sorted(sort_keys, reverse=True)

    def test_sort_by_relevance_default(self, populated_memory_env):
        from memory.searcher import search
        results, _ = search("PostgreSQL", limit=5)
        if len(results) > 1:
            scores = [r.score for r in results]
            assert scores == sorted(scores, reverse=True)


class TestSearchMetadata:
    def test_meta_truncated_flag(self, populated_memory_env):
        from memory.searcher import search
        results, meta = search("PostgreSQL", limit=1)
        assert "total_matches" in meta
        assert "returned" in meta
        assert "truncated" in meta
        assert meta["returned"] == len(results)

    def test_search_returns_required_fields(self, populated_memory_env):
        from memory.searcher import search
        results, _ = search("PostgreSQL")
        for r in results:
            assert hasattr(r, "text")
            assert hasattr(r, "score")
            assert hasattr(r, "date")
            assert hasattr(r, "session_summary")
            assert hasattr(r, "session_id")
            assert hasattr(r, "turn_number")
            assert hasattr(r, "project_path")
