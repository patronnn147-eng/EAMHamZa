"""Shared Excel-export helpers for admin_work_orders.py / cheftech_work_orders.py."""


def itv_str(itv, attr, default="N/A"):
    """Return attribute from intervention ORM, or default for falsy/absent values."""
    return (getattr(itv, attr, None) or default) if itv else default


def autofit_columns(worksheet) -> None:
    """Set each Excel column width to fit its longest value (max 60 chars)."""
    for col_cells in worksheet.columns:
        max_length = max(
            (len(str(cell.value)) for cell in col_cells if cell.value),
            default=0,
        )
        worksheet.column_dimensions[col_cells[0].column_letter].width = min(max_length + 4, 60)
