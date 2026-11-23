from classic_cloud.model import pending_frame, filter_pending, summary


def test_header_driven_sections_and_raw_status():
    upper=[None,'No.','구분','Unit명','수정 할 사항']
    lower=[None,'No.','구분','Unit명','내용','확인일','호기']
    rows=[upper,[None,1,'SW','GUI','요청','불가',None,'-','12월2주차',None,'설명','O (SW 1번)','미적용']]
    rows += [[]]*45
    rows += [lower,[None,1,'SW','GUI','조치','2026-10-01','공통','2026-11-01','2026-11-02','O','진행',None,'확인 필요']]
    f=pending_frame({'previews':{'고객사요청':{'rows':rows}}})
    assert len(f)==2 and f.ID.is_unique
    assert list(f['상태'])==['확인 필요','완료']
    assert f.iloc[0]['검토 결과']=='불가'
    assert f.iloc[0]['기존 펜딩 중복 여부']=='O (SW 1번)'
    assert f.iloc[1]['45호기 적용 여부']=='확인 필요'
    assert f.iloc[1]['설비']=='공통'
    assert len(filter_pending(f,scope='고객사 요청'))==2
    assert filter_pending(f,scope='주요 펜딩').empty
    assert summary(f,'범위').iloc[0]['전체']==2
    assert summary(f,'범위').iloc[0]['확인 필요']==1
