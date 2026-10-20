# 38 · Capacity modes: on-demand vs provisioned

**Run:** `just run 38`

## Problem

DynamoDB bills for throughput in one of two ways. Pick wrong and you either overpay a lot, or get throttled when traffic spikes.

## Pattern

**Start on on-demand. Move to provisioned + auto scaling once traffic is steady and predictable.**

| Mode                       | You pay for                         | Best for                                      |
|----------------------------|-------------------------------------|-----------------------------------------------|
| On-demand (`PAY_PER_REQUEST`) | each request (RRU / WRU)         | new apps, spiky or unknown traffic, dev/test, low volume |
| Provisioned + auto scaling | capacity per hour, used or not      | steady, predictable traffic at scale          |
| Provisioned + reserved capacity | 1- or 3-year commitment        | large, stable baseline                        |

Capacity-unit maths (same for both modes):

- **1 RCU** = 1 strongly consistent read/sec of up to 4 KB, *or* 2 eventually consistent reads.
- **1 WCU** = 1 write/sec of up to 1 KB.
- Transactions cost **2x**. Sizes round **up** (a 1.1 KB write is 2 WCU).

Example from the script: 3 KB items, 500 reads/s, 100 writes/s → 500 RCU strong (250 eventual), 300 WCU.

Auto scaling uses Application Auto Scaling with a target-tracking policy (e.g. keep utilization at 70%). The script prints the calls; DynamoDB Local doesn't have that service.

## Why

- **On-demand** needs no capacity planning, never throttles for "too little provisioned", and costs nothing when idle.
- **Provisioned** is roughly 5–7x cheaper per request at sustained utilization.

## Trade-offs

- On-demand gets expensive at high, steady volume.
- Provisioned auto scaling reacts in minutes, not seconds. A sudden spike can throttle before it scales. Burst capacity (up to 5 minutes of unused capacity) helps a little.
- On-demand still has limits. A new on-demand table instantly handles up to about 2x its previous peak, and can scale further over time. You can also set a maximum throughput per table as a cost guard.

## Gotchas

- Per-partition limits apply in both modes: about **3,000 RCU / 1,000 WCU per partition key**. A hot key throttles no matter how much capacity the table has ([35](../../07-performance-and-scale/35-write-sharding/35-write-sharding.md), [34](../../07-performance-and-scale/34-high-cardinality-keys/34-high-cardinality-keys.md)).
- GSIs have their own capacity in provisioned mode. An under-provisioned GSI throttles writes to the **base table**.
- You can only switch modes a limited number of times per 24 hours.
- Look at `ConsumedCapacity` (`ReturnConsumedCapacity="TOTAL"`) to measure real costs before choosing ([13](../../03-querying/13-filter-expressions-cost/13-filter-expressions-cost.md)).
