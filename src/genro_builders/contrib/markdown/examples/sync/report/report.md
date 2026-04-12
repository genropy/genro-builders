# Monthly Report — March 2026

This report summarizes the key metrics for the month.

## Summary

Revenue increased by 15% compared to February.

Customer satisfaction score: 4.7/5.0

## Sales by Region

| Region | Revenue | Growth |
| --- | --- | --- |
| North | $120,000 | +12% |
| South | $95,000 | +18% |
| East | $110,000 | +8% |
| West | $85,000 | +22% |

## Query Used

```sql
SELECT region, SUM(amount) AS revenue
FROM sales
WHERE month = '2026-03'
GROUP BY region
ORDER BY revenue DESC;
```

## Next Steps

- Expand marketing in West region
- Review pricing strategy for South
- Schedule Q2 planning meeting