# EasyIQ API Analysis and POC Results

## Overview
This document analyzes different approaches to extracting ugeplan (weekly plan) and lektier (homework) data from EasyIQ systems.

## Current Implementation Analysis

### Token-Based Approach (Current)
Our current implementation uses:
1. **Authentication**: Aula/Unilogin flow to get session
2. **Widget Discovery**: Get available widgets from Aula API
3. **Token Generation**: Get bearer tokens for specific EasyIQ widgets
4. **API Calls**: Use tokens to call EasyIQ API endpoints

**Results from testing:**
- ✅ Authentication works successfully
- ✅ Widget discovery works
- ✅ Token generation works
- ❌ **Ugeplan**: Returns error "Institutionen har ikke licens til EasyIQ Ugeplan widget"
- ❌ **Lektier**: Returns 404 error

### Chrome DevTools Direct Approach
From the Chrome DevTools request provided:
```
URL: https://skoleportal.easyiqcloud.dk/Calendar/CalendarGetWeekplanEvents
Method: GET
Parameters:
- loginId=xxxxxx
- date=2025-09-15T06:54:24.612Z
- activityFilter=2091719
- courseFilter=-1
- textFilter=
- ownWeekPlan=false
Authentication: Cookie-based (credentials: "include")
```

**Key Differences:**
1. **Direct portal access**: Calls `skoleportal.easyiqcloud.dk` directly
2. **Cookie authentication**: Uses session cookies instead of bearer tokens
3. **Different endpoint**: Uses `/Calendar/CalendarGetWeekplanEvents` instead of EasyIQ API
4. **LoginId parameter**: Requires a specific loginId (xxxxxx in the example)

## POC Testing Results

### Attempt 1: Direct EasyIQ Portal Access
- **Result**: 403 Forbidden
- **Issue**: Cannot access EasyIQ portal directly without proper authentication

### Attempt 2: Aula Authentication → EasyIQ Portal
- **Result**: 403 Forbidden  
- **Issue**: Even after successful Aula authentication, EasyIQ portal rejects access
- **Observation**: EasyIQ portal requires separate authentication flow

## Key Findings

### 1. Institution License Issues
The current token-based approach reveals that the test institutions don't have licenses for EasyIQ widgets:
- Hornbæk Skole: No license for EasyIQ Ugeplan widget
- Børnehuset Æblehaven: No license for EasyIQ Ugeplan widget

### 2. Different Authentication Systems
The Chrome DevTools request suggests that:
- EasyIQ portal (`skoleportal.easyiqcloud.dk`) is a separate system
- It requires direct login to the EasyIQ portal (not just Aula)
- It uses cookie-based authentication
- It has a different API structure

### 3. LoginId Parameter
The `loginId=xxxxxx` parameter in the Chrome DevTools request suggests:
- Each user has a specific loginId in the EasyIQ system
- This ID is different from Aula user IDs
- It's required for API calls

## Recommendations

### Option 1: Fix Current Token-Based Approach
**Pros:**
- Already implemented and working for institutions with licenses
- Uses official Aula API integration
- More maintainable

**Cons:**
- Requires institutions to have EasyIQ widget licenses
- May not work for all schools

**Action Items:**
- Test with an institution that has EasyIQ licenses
- Verify API endpoints and parameters
- Check if different widget IDs are needed

### Option 2: Implement Direct EasyIQ Portal Approach
**Pros:**
- May work for institutions without widget licenses
- Direct access to EasyIQ data
- Matches working Chrome DevTools approach

**Cons:**
- Requires reverse engineering EasyIQ portal authentication
- More complex authentication flow
- May be less stable (not official API)
- Need to discover how to get loginId

**Action Items:**
- Research EasyIQ portal login flow
- Find how to obtain loginId for users
- Implement cookie-based authentication
- Test with institutions that use EasyIQ portal directly

### Option 3: Hybrid Approach
**Pros:**
- Fallback mechanism for different institution types
- Maximum compatibility

**Cons:**
- More complex implementation
- Harder to maintain

## Next Steps

1. **Immediate**: Test current implementation with an institution that has EasyIQ licenses
2. **Research**: Investigate EasyIQ portal authentication flow
3. **Implement**: Create direct portal authentication if needed
4. **Test**: Validate both approaches with real data

## Technical Notes

### Current API Endpoints
- **Ugeplan**: `https://api.easyiqcloud.dk/api/aula/weekplaninfo` (POST with bearer token)
- **Lektier**: `https://api.easyiqcloud.dk/api/aula/opgaveliste` (GET with bearer token)

### Direct Portal Endpoints (from Chrome DevTools)
- **Ugeplan**: `https://skoleportal.easyiqcloud.dk/Calendar/CalendarGetWeekplanEvents` (GET with cookies)

### Authentication Comparison
| Aspect | Current (Token) | Direct Portal (Cookie) |
|--------|----------------|------------------------|
| Initial Auth | Aula/Unilogin | EasyIQ Portal Login |
| API Auth | Bearer Token | Session Cookies |
| User ID | Aula Child ID | EasyIQ LoginId |
| Endpoint | api.easyiqcloud.dk | skoleportal.easyiqcloud.dk |

## Conclusion

The Chrome DevTools request reveals a different approach to accessing EasyIQ data that may bypass the widget license requirements. However, it requires implementing a separate authentication flow for the EasyIQ portal. The current token-based approach is working correctly but is limited by institution licenses.

**Recommendation**: Investigate the direct portal approach as it may provide broader compatibility with different institution setups.