nums=[9,-3,3,-1,6,-5]
n=len(nums)
result=0
for i in range(n):
    sum=0
    for j in range(i,n):
        sum+=nums[j]
        if sum==0:
            result=max(result,j-i+1)
print(result)


i=0
j=len(nums)
result=0
count=0
for k in range(n):
    result+=sum(nums[i:j])
    if result==0:
        count=max(count,n-i)
    if nums[i]>nums[j]:
        j-=1
    else :
        i+=1
print(count)
