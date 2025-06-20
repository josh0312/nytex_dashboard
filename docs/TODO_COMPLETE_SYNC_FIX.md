# TODO: Fix Complete Sync Archived Item Handling

## Issue Summary
The complete sync process (used for emergency recovery) doesn't properly handle archived items in the catalog and vendor sync functions, which could lead to archived items being imported into the database.

## Background
- **Current Issue**: Complete sync may import archived items into production database
- **Impact**: Low (complete sync is only used in extreme circumstances)  
- **Status**: Incremental sync properly handles archived items ✅

## Root Cause
The complete sync functions may not have the proper filtering for archived items that the incremental sync has implemented.

## Required Changes
1. **Review** complete sync functions in `app/routes/admin.py`
2. **Add** proper archived item filtering to catalog sync
3. **Add** proper archived item filtering to vendor sync
4. **Test** complete sync process safely (without affecting production data)

## Files to Review
- `app/routes/admin.py` - Complete sync endpoints
- Compare with incremental sync logic in `app/services/incremental_sync_service.py`

## Testing Requirements
- Test complete sync in development environment only
- Verify archived items are properly excluded  
- Ensure data integrity is maintained

## Priority
**Low** - Complete sync is emergency-only feature, incremental sync is working correctly

## Status
- [ ] Review complete sync logic
- [ ] Implement archived item filtering
- [ ] Test in development
- [ ] Document changes

---
**Created**: 2025-06-20  
**Priority**: Low  
**Labels**: enhancement, sync, low-priority 