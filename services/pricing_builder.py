# services/pricing_builder.py

class PricingBuilder:

    def build_comparison_rows(
        self,
        supplier_records,
        benchmark_lookup,
        key_field,
        comparison_fields,
    ):
        rows = []

        for supplier_record in supplier_records:

            row = {}

            row["record"] = supplier_record

            benchmark_record = benchmark_lookup.get(
                str(
                    supplier_record.get_value(
                        key_field
                    )
                )
            )

            row["benchmark_record"] = (
                benchmark_record
            )

            for field_name in comparison_fields:

                row[field_name] = (
                    supplier_record.get_value(
                        field_name
                    )
                )

            rows.append(row)

        return rows