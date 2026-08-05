# services/benchmark_service.py

class BenchmarkService:

    def build_benchmark_lookup(
        self,
        benchmark_records,
        key_field,
    ):
        lookup = {}

        for record in benchmark_records:

            key = record.get_value(
                key_field
            )

            if key is None:
                continue

            lookup[str(key).strip()] = record

        return lookup

    def match_record(
        self,
        supplier_record,
        benchmark_lookup,
        key_field,
    ):
        key = supplier_record.get_value(
            key_field
        )

        if key is None:
            return None

        return benchmark_lookup.get(
            str(key).strip()
        )

    def get_benchmark_value(
        self,
        supplier_record,
        benchmark_lookup,
        key_field,
        benchmark_field,
    ):
        benchmark_record = self.match_record(
            supplier_record,
            benchmark_lookup,
            key_field,
        )

        if benchmark_record is None:
            return None

        return benchmark_record.get_value(
            benchmark_field
        )