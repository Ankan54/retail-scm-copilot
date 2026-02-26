import { T, fmt } from "./api";

export const DEALERS = [
    { id: 1, name: "Sharma General Store", city: "New Delhi", lat: 28.61, lng: 77.23, category: "A", health: "healthy", revenue: 892000, outstanding: 45000, lastVisit: "2 days ago", commitments: 3, salesRep: "Ankan Bera" },
    { id: 2, name: "Gupta Traders", city: "East Delhi", lat: 28.63, lng: 77.29, category: "A", health: "at-risk", revenue: 654000, outstanding: 320000, lastVisit: "25 days ago", commitments: 1, salesRep: "Deepak Singh" },
    { id: 3, name: "Patel Enterprises", city: "South Delhi", lat: 28.52, lng: 77.21, category: "B", health: "healthy", revenue: 523000, outstanding: 12000, lastVisit: "5 days ago", commitments: 2, salesRep: "Sunil Verma" },
    { id: 4, name: "Reddy & Sons", city: "West Delhi", lat: 28.65, lng: 77.10, category: "A", health: "healthy", revenue: 987000, outstanding: 67000, lastVisit: "1 day ago", commitments: 4, salesRep: "Ankan Bera" },
    { id: 5, name: "Mehta Supplies", city: "North Delhi", lat: 28.72, lng: 77.17, category: "C", health: "critical", revenue: 123000, outstanding: 189000, lastVisit: "45 days ago", commitments: 0, salesRep: "Amit Sharma" },
    { id: 6, name: "Singh Brothers", city: "Central Delhi", lat: 28.64, lng: 77.22, category: "B", health: "healthy", revenue: 456000, outstanding: 23000, lastVisit: "3 days ago", commitments: 2, salesRep: "Ankan Bera" },
    { id: 7, name: "Joshi Retail Hub", city: "South Delhi", lat: 28.54, lng: 77.25, category: "B", health: "at-risk", revenue: 345000, outstanding: 156000, lastVisit: "18 days ago", commitments: 1, salesRep: "Sunil Verma" },
    { id: 8, name: "Das Trading Co.", city: "East Delhi", lat: 28.62, lng: 77.31, category: "A", health: "healthy", revenue: 789000, outstanding: 34000, lastVisit: "4 days ago", commitments: 3, salesRep: "Deepak Singh" },
    { id: 9, name: "Kumar Agencies", city: "North Delhi", lat: 28.73, lng: 77.20, category: "B", health: "healthy", revenue: 567000, outstanding: 89000, lastVisit: "6 days ago", commitments: 2, salesRep: "Amit Sharma" },
    { id: 10, name: "Nair Distributors", city: "West Delhi", lat: 28.63, lng: 77.07, category: "C", health: "at-risk", revenue: 234000, outstanding: 210000, lastVisit: "30 days ago", commitments: 0, salesRep: "Ankan Bera" },
    { id: 11, name: "Bose Wholesale", city: "East Delhi", lat: 28.60, lng: 77.33, category: "C", health: "healthy", revenue: 198000, outstanding: 15000, lastVisit: "7 days ago", commitments: 1, salesRep: "Deepak Singh" },
    { id: 12, name: "Agarwal Stores", city: "Central Delhi", lat: 28.66, lng: 77.24, category: "A", health: "healthy", revenue: 876000, outstanding: 56000, lastVisit: "2 days ago", commitments: 3, salesRep: "Ankan Bera" },
];

export const REVENUE_DATA = [
    { month: "Apr", revenue: 3669470, target: 3500000, collections: 3200000 },
    { month: "May", revenue: 3247110, target: 3500000, collections: 2900000 },
    { month: "Jun", revenue: 2665880, target: 3200000, collections: 2400000 },
    { month: "Jul", revenue: 2888600, target: 3200000, collections: 2600000 },
    { month: "Aug", revenue: 2303040, target: 3000000, collections: 2100000 },
    { month: "Sep", revenue: 2530350, target: 3000000, collections: 2300000 },
    { month: "Oct", revenue: 3140240, target: 3400000, collections: 2900000 },
    { month: "Nov", revenue: 3219560, target: 3400000, collections: 3000000 },
    { month: "Dec", revenue: 3588010, target: 3600000, collections: 3300000 },
    { month: "Jan", revenue: 2633740, target: 3200000, collections: 2400000 },
    { month: "Feb", revenue: 1826170, target: 3000000, collections: 1700000 },
];

export const COMMITMENT_DATA = [
    { status: "Converted", count: 275, value: 1820000, color: "#22c55e" },
    { status: "Pending", count: 90, value: 780000, color: "#f59e0b" },
    { status: "Partial", count: 60, value: 540000, color: "#6366f1" },
    { status: "Expired", count: 60, value: 340000, color: "#ef4444" },
    { status: "Cancelled", count: 15, value: 120000, color: "#8b8fad" },
];

export const PIPELINE_BY_WEEK = [
    { week: "W1", new: 8, confirmed: 5, fulfilled: 12, overdue: 1 },
    { week: "W2", new: 11, confirmed: 7, fulfilled: 9, overdue: 2 },
    { week: "W3", new: 6, confirmed: 9, fulfilled: 14, overdue: 1 },
    { week: "W4", new: 9, confirmed: 4, fulfilled: 11, overdue: 3 },
];

export const SALES_REPS = [
    { name: "Ankan Bera", territory: "Central/West Delhi", dealers: 18, visits: 28, target: 1200000, achieved: 1080000, commitments: 8, conversion: 78 },
    { name: "Deepak Singh", territory: "East Delhi", dealers: 9, visits: 22, target: 1000000, achieved: 870000, commitments: 5, conversion: 65 },
    { name: "Sunil Verma", territory: "South Delhi", dealers: 9, visits: 30, target: 1100000, achieved: 1210000, commitments: 11, conversion: 85 },
    { name: "Amit Sharma", territory: "North Delhi", dealers: 9, visits: 25, target: 950000, achieved: 920000, commitments: 7, conversion: 72 },
];

export const RECENT_ACTIVITIES = [
    { type: "visit", text: "Ankan Bera visited Sharma General Store", detail: "Commitment: 500 cases Premium Soap by next Tuesday", time: "2 hrs ago", icon: "visit" },
    { type: "commitment", text: "New commitment from Das Trading Co.", detail: "\u20B93.4L order for Industrial Cleaners, delivery Mar 5", time: "4 hrs ago", icon: "commitment" },
    { type: "alert", text: "Gupta Traders flagged at-risk", detail: "\u20B93.2L overdue, no visit in 25 days", time: "6 hrs ago", icon: "alert" },
    { type: "order", text: "Order confirmed: Reddy & Sons", detail: "\u20B92.8L \u2014 converted from commitment", time: "8 hrs ago", icon: "order" },
    { type: "collection", text: "Collection \u20B945K from Sharma General Store", detail: "Collected by Ankan Bera during visit", time: "2 hrs ago", icon: "collection" },
    { type: "visit", text: "Amit Sharma visited Kumar Agencies", detail: "Product demo new range, follow-up scheduled", time: "1 day ago", icon: "visit" },
];

export const DEALER_BY_CAT = [
    { name: "Platinum (A)", value: 5, color: "#6366f1" },
    { name: "Gold (B)", value: 15, color: "#f59e0b" },
    { name: "Silver (C)", value: 25, color: "#8b8fad" },
];

export const CHAT_SUGGESTIONS = [
    "Brief me for Sharma General Store visit",
    "Plan my visits for this week",
    "Show at-risk dealers in my region",
    "What's the demand forecast for Premium Soap?",
    "Kitna collection hua is mahine?",
    "Show commitment pipeline for my territory",
];
