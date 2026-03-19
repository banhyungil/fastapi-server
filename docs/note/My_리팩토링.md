1. RESTfull api 설계

- segment 시작은 resource로 시작
- 이후 segment에서는 명사/동사 를 사용해도됨.
- resource는 복수형으로 사용한다.

2. router, service, repo 일관성
- resource 세그먼트를 사용한 경우는 파일명도 resource로 시작한다.
- service, repo는 postfix를 사용하여 일관된 접근을 할 수 있도록 한다.
- 서비스가 커지는 경우는 내부 모듈로 분리하여 사용한다. 이떄 service postfix는 사용하지않는다.
    - ex. cache.py, crop.py
    - 별도 폴더로 분리해도 될것도 같지만 후에 진행하자. (utils로 빼기에는 서비스 성격이 강하긴 함)
 


 